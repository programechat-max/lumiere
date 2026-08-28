"""
GDPR/gizlilik iş mantığı (PROMPT 11): veri dışa aktarma, hesap silme (30 günlük
ödül süresiyle), onay (consent) yönetimi."""
import datetime
import logging
import secrets
from typing import Optional

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

import models
from database import SessionLocal

logger = logging.getLogger(__name__)

DELETION_GRACE_PERIOD_DAYS = 30


def build_user_data_export(user_id: int, db: Optional[Session] = None) -> dict:
    """Kullanıcının TÜM kişisel verisini makine tarafından okunabilir (JSON) formatta
    toplar - GDPR "right to access / data portability" gerekliliği.

    `db` verilmezse (Celery task/standalone çağrıları için) kendi oturumunu açar;
    verilirse (örn. test'lerde aynı fixture oturumu) onu kullanır."""
    own_session = db is None
    if own_session:
        db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            return {}
        data = {
            "user": jsonable_encoder(user, exclude={"hashed_password", "mfa_secret"}),
            "profile": jsonable_encoder(db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).first()),
            "workout_logs": jsonable_encoder(db.query(models.WorkoutLog).filter(models.WorkoutLog.user_id == user_id).all()),
            "nutrition_logs": jsonable_encoder(db.query(models.NutritionLog).filter(models.NutritionLog.user_id == user_id).all()),
            "body_metrics": jsonable_encoder(db.query(models.BodyMetric).filter(models.BodyMetric.user_id == user_id).all()),
            "memories": jsonable_encoder(db.query(models.UserMemory).filter(models.UserMemory.user_id == user_id).all()),
            "chat_messages": jsonable_encoder(db.query(models.ChatMessage).filter(models.ChatMessage.user_id == user_id).all()),
            "daily_checkins": jsonable_encoder(db.query(models.DailyCheckIn).filter(models.DailyCheckIn.user_id == user_id).all()),
            "meal_plan_items": jsonable_encoder(db.query(models.MealPlanItem).filter(models.MealPlanItem.user_id == user_id).all()),
            "subscription": jsonable_encoder(db.query(models.Subscription).filter(models.Subscription.user_id == user_id).first()),
            "invoices": jsonable_encoder(db.query(models.Invoice).filter(models.Invoice.user_id == user_id).all()),
            "consents": jsonable_encoder(db.query(models.Consent).filter(models.Consent.user_id == user_id).all()),
            "exported_at": datetime.datetime.utcnow().isoformat(),
        }
        db.add(models.DataExportRequest(user_id=user_id, status="ready"))
        db.commit()
        return data
    finally:
        if own_session:
            db.close()


def request_account_deletion(db: Session, user_id: int) -> models.AccountDeletionRequest:
    existing = (
        db.query(models.AccountDeletionRequest)
        .filter(models.AccountDeletionRequest.user_id == user_id, models.AccountDeletionRequest.status == "pending")
        .first()
    )
    if existing:
        return existing
    now = datetime.datetime.utcnow()
    request = models.AccountDeletionRequest(
        user_id=user_id,
        requested_at=now,
        scheduled_for=now + datetime.timedelta(days=DELETION_GRACE_PERIOD_DAYS),
        status="pending",
        cancel_token=secrets.token_urlsafe(24),
    )
    db.add(request)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.deletion_requested_at = now
    db.commit()
    db.refresh(request)
    return request


def cancel_account_deletion(db: Session, user_id: int, cancel_token: str) -> bool:
    request = (
        db.query(models.AccountDeletionRequest)
        .filter(
            models.AccountDeletionRequest.user_id == user_id,
            models.AccountDeletionRequest.status == "pending",
            models.AccountDeletionRequest.cancel_token == cancel_token,
        )
        .first()
    )
    if not request:
        return False
    request.status = "canceled"
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.deletion_requested_at = None
    db.commit()
    return True


def execute_account_deletion(user_id: int) -> None:
    """30 günlük ödül süresi dolduğunda çağrılır (bkz. tasks.delete_account_task).
    Faturalar (7 yıl yasal saklama) HARİÇ tüm kullanıcı verisini kademeli siler."""
    db = SessionLocal()
    try:
        tables_to_wipe = [
            models.ChatMessage, models.UserMemory, models.WorkoutLog, models.NutritionLog,
            models.BodyMetric, models.DailyCheckIn, models.MealPlanItem, models.UserDeviceToken,
            models.NotificationSettings, models.PushNotificationLog, models.Consent,
        ]
        for table in tables_to_wipe:
            db.query(table).filter(table.user_id == user_id).delete()

        for program in db.query(models.WorkoutProgram).filter(models.WorkoutProgram.user_id == user_id).all():
            db.query(models.Exercise).filter(models.Exercise.program_id == program.id).delete()
            db.delete(program)

        # Fatura kayıtları YASAL SAKLAMA (7 yıl) nedeniyle silinmez, sadece kullanıcıdan koparılmaz -
        # zaten user_id referansı denetim/muhasebe amaçlı korunur.
        request = (
            db.query(models.AccountDeletionRequest)
            .filter(models.AccountDeletionRequest.user_id == user_id, models.AccountDeletionRequest.status == "pending")
            .first()
        )
        if request:
            request.status = "completed"
            request.completed_at = datetime.datetime.utcnow()

        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            user.is_active = False
            user.full_name = "Silinmiş Kullanıcı"
            user.email = f"deleted-{user_id}-{secrets.token_hex(4)}@deleted.local"
            user.hashed_password = secrets.token_hex(32)

        db.commit()
        logger.info("Hesap silme tamamlandı: user_id=%s", user_id)
    finally:
        db.close()


def record_consent(db: Session, user_id: int, consent_type: str, granted: bool, ip_address: Optional[str], user_agent: Optional[str], policy_version: str = "1.0") -> models.Consent:
    consent = models.Consent(
        user_id=user_id, consent_type=consent_type, granted=granted,
        ip_address=ip_address, user_agent=user_agent, policy_version=policy_version,
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    return consent


def get_latest_consents(db: Session, user_id: int) -> dict:
    consents = (
        db.query(models.Consent)
        .filter(models.Consent.user_id == user_id)
        .order_by(models.Consent.created_at.desc())
        .all()
    )
    latest = {}
    for c in consents:
        if c.consent_type not in latest:
            latest[c.consent_type] = {"granted": c.granted, "updated_at": c.created_at}
    return latest


def find_pending_deletions_due() -> list:
    """Ödül süresi dolmuş, henüz işlenmemiş silme taleplerini döner (Celery Beat/cron ile çağrılır)."""
    db = SessionLocal()
    try:
        now = datetime.datetime.utcnow()
        due = (
            db.query(models.AccountDeletionRequest)
            .filter(models.AccountDeletionRequest.status == "pending", models.AccountDeletionRequest.scheduled_for <= now)
            .all()
        )
        return [r.user_id for r in due]
    finally:
        db.close()
