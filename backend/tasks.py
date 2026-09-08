"""
Celery görev tanımları (PROMPT 5). Her görev idempotent'tir (güvenle tekrar
denenebilir) ve ilerlemesini `job_service` üzerinden JobStatus tablosuna yazar.

REDIS_URL tanımlı değilse bu görevler `celery_app`'in EAGER modu sayesinde
doğrudan çağıran süreç içinde (senkron) çalışır - fonksiyonel davranış aynıdır,
sadece gerçek paralellik/kuyruklama olmaz."""
import logging
import os
import sys
import importlib

from celery import Celery
from celery.utils.log import get_task_logger

import job_service
from celery_app import celery_app

logger = get_task_logger(__name__)


def _load_ai_core():
    """Celery child süreçlerinde /app her zaman sys.path'e ekli olmayabilir.
    Görevleri çalışma dizinine bağımlı bırakmadan backend modülünü yükle."""
    module_dir = os.path.dirname(os.path.abspath(__file__))
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    return importlib.import_module("ai_core")

RETRY_KWARGS = {"max_retries": 3, "countdown": 3}  # 3s, 9s, 27s (autoretry_for ile üstel için bkz. retry_backoff


def _base_task(name, soft_time_limit, queue_hint=None):
    return celery_app.task(
        bind=True,
        name=name,
        autoretry_for=(Exception,),
        retry_backoff=3,
        retry_backoff_max=27,
        retry_jitter=False,
        max_retries=3,
        soft_time_limit=soft_time_limit,
        acks_late=True,
    )


@_base_task("tasks.analyze_video_task", soft_time_limit=300)
def analyze_video_task(self, video_bytes: bytes, mime_type: str, user_id: int):
    job_service.update_job(self.request.id, status="started", progress_percent=10)
    ai_core = _load_ai_core()
    try:
        result = ai_core.analyze_physique_media(video_bytes, mime_type, db=None, user_id=user_id)
        job_service.update_job(self.request.id, status="success", progress_percent=100, result={"ok": True})
        return result
    except Exception as exc:
        job_service.update_job(self.request.id, status="failure", error_message=str(exc))
        raise


@_base_task("tasks.analyze_video_file_task", soft_time_limit=300)
def analyze_video_file_task(self, file_path: str, mime_type: str, user_id: int):
    """Paylaşılan medya volume'ündeki videoyu işleyip sonucu JobStatus'a yazar.
    HTTP isteği Gemini'yi beklemez; worker tamamlandığında istemci job endpointinden
    sonucu alır."""
    job_service.update_job(self.request.id, status="started", progress_percent=10)
    ai_core = _load_ai_core()
    succeeded = False
    try:
        with open(file_path, "rb") as media_file:
            video_bytes = media_file.read()
        job_service.update_job(self.request.id, status="progress", progress_percent=30)
        result = ai_core.analyze_physique_media(video_bytes, mime_type, db=None, user_id=user_id)
        job_service.update_job(self.request.id, status="success", progress_percent=100, result=result)
        succeeded = True
        return result
    except Exception as exc:
        # `autoretry_for` bu istisnayı yeniden kuyruğa alır. Ara denemelerde
        # görevi failure olarak işaretlemek istemci polling'ini erken kesiyor
        # ve aynı task yeniden çalışırken kullanıcıya yanlış hata gösteriyordu.
        # Sadece son denemede kalıcı failure yaz; önceki denemelerde progress
        # durumunu koru ve güvenli bir açıklama bırak.
        if self.request.retries >= self.max_retries:
            job_service.update_job(self.request.id, status="failure", progress_percent=100, error_message=str(exc))
        else:
            retry_no = self.request.retries + 1
            job_service.update_job(
                self.request.id,
                status="progress",
                progress_percent=30,
                error_message=f"Geçici analiz hatası; {retry_no}. tekrar denemesi planlandı.",
            )
        raise
    finally:
        # Autoretry sırasında dosyayı silme; sonraki deneme aynı medyayı
        # okuyabilmeli. Başarıda veya son denemede temizlik yap.
        if succeeded or self.request.retries >= self.max_retries:
            try:
                os.remove(file_path)
            except OSError:
                pass


@_base_task("tasks.analyze_food_photo_task", soft_time_limit=60)
def analyze_food_photo_task(self, image_bytes: bytes, mime_type: str, user_id: int, save: bool = True):
    job_service.update_job(self.request.id, status="started", progress_percent=10)
    ai_core = _load_ai_core()
    try:
        result = ai_core.analyze_photo(image_bytes, mime_type, db=None, save=save, user_id=user_id)
        job_service.update_job(self.request.id, status="success", progress_percent=100, result={"ok": True})
        return result
    except Exception as exc:
        job_service.update_job(self.request.id, status="failure", error_message=str(exc))
        raise


@_base_task("tasks.generate_ai_meal_plan_task", soft_time_limit=180)
def generate_ai_meal_plan_task(self, user_id: int, user_instruction: str = None):
    job_service.update_job(self.request.id, status="started", progress_percent=20)
    ai_core = _load_ai_core()
    from fastapi.encoders import jsonable_encoder
    try:
        plan = ai_core.generate_meal_plan(db=None, user_instruction=user_instruction, user_id=user_id)
        serialized = jsonable_encoder(plan)
        job_service.update_job(self.request.id, status="success", progress_percent=100, result={"meal_plan": serialized})
        return serialized
    except Exception as exc:
        job_service.update_job(self.request.id, status="failure", error_message=str(exc))
        raise


@_base_task("tasks.generate_ai_workout_program_task", soft_time_limit=180)
def generate_ai_workout_program_task(self, user_id: int, user_instruction: str = None):
    job_service.update_job(self.request.id, status="started", progress_percent=20)
    ai_core = _load_ai_core()
    try:
        programs = ai_core.generate_workout_program(db=None, user_instruction=user_instruction, user_id=user_id)
        job_service.update_job(self.request.id, status="success", progress_percent=100, result={"programs": programs})
        return programs
    except Exception as exc:
        job_service.update_job(self.request.id, status="failure", error_message=str(exc))
        raise


@_base_task("tasks.weekly_analysis_report_task", soft_time_limit=180)
def weekly_analysis_report_task(self, user_id: int):
    job_service.update_job(self.request.id, status="started", progress_percent=20)
    ai_core = _load_ai_core()
    try:
        analysis = ai_core.generate_weekly_analysis(db=None, user_id=user_id)
        send_push_notification_task.delay(user_id, "weekly_report", "Haftalık analizin hazır", "Jarvis bu haftaki ilerlemeni değerlendirdi, dashboard'dan incele.")
        job_service.update_job(self.request.id, status="success", progress_percent=100, result={"analysis": analysis})
        return analysis
    except Exception as exc:
        job_service.update_job(self.request.id, status="failure", error_message=str(exc))
        raise


@_base_task("tasks.send_email_notification_task", soft_time_limit=60)
def send_email_notification_task(self, to_email: str, subject: str, body: str):
    """SMTP sağlayıcısı yapılandırılana kadar e-postalar sadece loglanır (no-op).
    Üretimde bu fonksiyon SES/SendGrid/Postmark istemcisiyle değiştirilmelidir."""
    logger.info("[EMAIL] to=%s subject=%s body_len=%d (SMTP yapılandırılmadı - sadece loglandı)", to_email, subject, len(body))
    job_service.update_job(self.request.id, status="success", progress_percent=100, result={"sent": False, "reason": "smtp_not_configured"})
    return {"sent": False}


@_base_task("tasks.send_push_notification_task", soft_time_limit=30)
def send_push_notification_task(self, user_id: int, notification_type: str, title: str, body: str, deep_link: str = None):
    import notification_service
    from database import SessionLocal
    db = SessionLocal()
    try:
        result = notification_service.dispatch_to_user(db, user_id, notification_type, title, body, deep_link=deep_link)
        job_service.update_job(self.request.id, status="success", progress_percent=100, result=result)
        return result
    except Exception as exc:
        job_service.update_job(self.request.id, status="failure", error_message=str(exc))
        raise
    finally:
        db.close()


@_base_task("tasks.batch_send_scheduled_reminders_task", soft_time_limit=600)
def batch_send_scheduled_reminders_task(self, notification_type: str, title: str, body: str):
    """APScheduler/Celery Beat tarafından tetiklenen toplu hatırlatma görevi
    (örn. günlük check-in, haftalık rapor, hareketsizlik uyarısı)."""
    import models
    from database import SessionLocal
    db = SessionLocal()
    try:
        user_ids = [row[0] for row in db.query(models.User.id).filter(models.User.is_active == True).all()]  # noqa: E712
        sent = 0
        for uid in user_ids:
            send_push_notification_task.delay(uid, notification_type, title, body)
            sent += 1
        job_service.update_job(self.request.id, status="success", progress_percent=100, result={"queued": sent})
        return {"queued": sent}
    finally:
        db.close()


@_base_task("tasks.export_user_data_task", soft_time_limit=600)
def export_user_data_task(self, user_id: int):
    import privacy
    job_service.update_job(self.request.id, status="started", progress_percent=10)
    try:
        export = privacy.build_user_data_export(user_id)
        job_service.update_job(self.request.id, status="success", progress_percent=100, result={"ready": True, "size": len(str(export))})
        return export
    except Exception as exc:
        job_service.update_job(self.request.id, status="failure", error_message=str(exc))
        raise


@_base_task("tasks.delete_account_task", soft_time_limit=600)
def delete_account_task(self, user_id: int):
    import privacy
    job_service.update_job(self.request.id, status="started", progress_percent=10)
    try:
        privacy.execute_account_deletion(user_id)
        job_service.update_job(self.request.id, status="success", progress_percent=100, result={"deleted": True})
        return {"deleted": True}
    except Exception as exc:
        job_service.update_job(self.request.id, status="failure", error_message=str(exc))
        raise
