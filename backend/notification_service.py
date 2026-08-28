"""
Push bildirim iş mantığı: token yaşam döngüsü, kullanıcı tercihleri, sessiz saatler
(quiet hours) ve gönderim kayıtları (PROMPT 9)."""
import datetime
import logging
from typing import Optional

from sqlalchemy.orm import Session

import apns_client
import models

logger = logging.getLogger(__name__)


def register_device_token(db: Session, user_id: int, token: str, platform: str = "ios", device_name: Optional[str] = None) -> models.UserDeviceToken:
    existing = db.query(models.UserDeviceToken).filter(models.UserDeviceToken.device_token == token).first()
    if existing:
        # Token başka bir kullanıcıya kayıtlıysa (cihaz değişimi/yeniden yükleme), sahipliği güncelle.
        existing.user_id = user_id
        existing.is_active = True
        existing.last_seen_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    device = models.UserDeviceToken(user_id=user_id, device_token=token, platform=platform, device_name=device_name)
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def unregister_device_token(db: Session, user_id: int, token: str) -> bool:
    device = (
        db.query(models.UserDeviceToken)
        .filter(models.UserDeviceToken.device_token == token, models.UserDeviceToken.user_id == user_id)
        .first()
    )
    if not device:
        return False
    db.delete(device)
    db.commit()
    return True


def prune_invalid_token(db: Session, token: str) -> None:
    db.query(models.UserDeviceToken).filter(models.UserDeviceToken.device_token == token).delete()
    db.commit()


def get_or_create_settings(db: Session, user_id: int) -> models.NotificationSettings:
    settings_row = db.query(models.NotificationSettings).filter(models.NotificationSettings.user_id == user_id).first()
    if not settings_row:
        settings_row = models.NotificationSettings(user_id=user_id)
        db.add(settings_row)
        db.commit()
        db.refresh(settings_row)
    return settings_row


def update_settings(db: Session, user_id: int, data: dict) -> models.NotificationSettings:
    settings_row = get_or_create_settings(db, user_id)
    for key, value in data.items():
        if value is not None and hasattr(settings_row, key):
            setattr(settings_row, key, value)
    db.commit()
    db.refresh(settings_row)
    return settings_row


def is_within_quiet_hours(settings_row: models.NotificationSettings, now: Optional[datetime.time] = None) -> bool:
    now = now or datetime.datetime.now().time()
    try:
        start = datetime.datetime.strptime(settings_row.quiet_hours_start, "%H:%M").time()
        end = datetime.datetime.strptime(settings_row.quiet_hours_end, "%H:%M").time()
    except (ValueError, TypeError):
        return False
    if start <= end:
        return start <= now <= end
    return now >= start or now <= end  # gece yarısını aşan aralık (örn. 22:00-08:00)


def dispatch_to_user(db: Session, user_id: int, notification_type: str, title: str, body: str, deep_link: Optional[str] = None) -> dict:
    """Kullanıcının aktif tüm cihazlarına push gönderir; tercih/quiet-hours kontrolünden geçirir."""
    settings_row = get_or_create_settings(db, user_id)
    pref_map = {
        "daily_checkin": settings_row.daily_checkin_enabled,
        "workout_reminder": settings_row.workout_reminders_enabled,
        "weekly_report": settings_row.weekly_report_enabled,
        "inactivity": settings_row.inactivity_alerts_enabled,
        "billing": settings_row.billing_alerts_enabled,
    }
    if not pref_map.get(notification_type, True):
        return {"status": "skipped", "reason": "user_preference_disabled"}

    # Faturalandırma uyarıları kritik olduğundan sessiz saatlerde de gönderilir.
    if notification_type != "billing" and is_within_quiet_hours(settings_row):
        return {"status": "skipped", "reason": "quiet_hours"}

    devices = db.query(models.UserDeviceToken).filter(
        models.UserDeviceToken.user_id == user_id, models.UserDeviceToken.is_active == True  # noqa: E712
    ).all()
    if not devices:
        return {"status": "skipped", "reason": "no_active_devices"}

    results = []
    for device in devices:
        log_entry = models.PushNotificationLog(
            user_id=user_id, device_token=device.device_token, notification_type=notification_type,
            title=title, body=body, status="pending",
        )
        db.add(log_entry)
        db.commit()
        try:
            apns_client.send_push(device.device_token, title, body, deep_link=deep_link, thread_id=notification_type)
            log_entry.status = "sent"
            results.append({"device": device.device_token[:8], "status": "sent"})
        except apns_client.APNsError as exc:
            log_entry.status = "failed"
            log_entry.error_message = exc.reason
            results.append({"device": device.device_token[:8], "status": "failed", "reason": exc.reason})
            if exc.reason in apns_client.INVALID_TOKEN_REASONS:
                prune_invalid_token(db, device.device_token)
                logger.info("Geçersiz APNs token temizlendi: %s...", device.device_token[:8])
        db.commit()

    return {"status": "processed", "results": results}
