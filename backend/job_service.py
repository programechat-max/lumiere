"""
Arka plan iş takibi (PROMPT 5): her Celery görevi için ilerleme/durum bilgisini
veritabanına (JobStatus) yazar - frontend `/api/v1/jobs/{task_id}` ile polling
yapabilir."""
from typing import Optional
import datetime
import logging

from sqlalchemy.orm import Session

import models
from database import SessionLocal

logger = logging.getLogger(__name__)

# Worker/Redis tamamen kapalıyken apply_async broker'a kabul edilmiş görünebilir
# ve task DB'de sonsuza kadar pending kalabilir. API'nin status polling'i bu
# süreyi aşan kayıtları deterministik biçimde sonlandırır.
STALE_JOB_TIMEOUT_MINUTES = 15


def create_job(db: Session, task_id: str, job_type: str, user_id: Optional[int] = None) -> models.JobStatus:
    job = models.JobStatus(task_id=task_id, job_type=job_type, user_id=user_id, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_job(task_id: str, status: str, progress_percent: Optional[int] = None, result: Optional[dict] = None, error_message: Optional[str] = None) -> None:
    """Celery worker/eager görev içinden çağrılır - kendi DB oturumunu açar/kapatır."""
    import datetime
    db = SessionLocal()
    try:
        job = db.query(models.JobStatus).filter(models.JobStatus.task_id == task_id).first()
        if not job:
            return
        job.status = status
        if progress_percent is not None:
            job.progress_percent = progress_percent
        if result is not None:
            job.result = result
        if error_message is not None:
            job.error_message = error_message
        if status == "success":
            # Önceki bir autoretry denemesinin açıklaması başarılı sonuca
            # sarkmasın; istemci yalnızca gerçekten son durumun hata alanını
            # göstermelidir.
            job.error_message = None
        if status in ("success", "failure"):
            job.completed_at = datetime.datetime.utcnow()
        db.commit()
    finally:
        db.close()


def get_job(db: Session, task_id: str, user_id: Optional[int] = None) -> Optional[models.JobStatus]:
    query = db.query(models.JobStatus).filter(models.JobStatus.task_id == task_id)
    if user_id is not None:
        query = query.filter(models.JobStatus.user_id == user_id)
    job = query.first()
    if not job:
        return None

    if job.status in ("pending", "started", "progress") and job.created_at:
        created_at = job.created_at
        # PostgreSQL UTC timestamp'ı naive, farklı driver'lar aware döndürebilir.
        if created_at.tzinfo is not None:
            created_at = created_at.replace(tzinfo=None)
        age = datetime.datetime.utcnow() - created_at
        if age.total_seconds() > STALE_JOB_TIMEOUT_MINUTES * 60:
            job.status = "failure"
            job.progress_percent = 100
            job.error_message = (
                "Analiz görevi zaman aşımına uğradı. Worker/API bağlantısını kontrol edip videoyu tekrar gönderin."
            )
            job.completed_at = datetime.datetime.utcnow()
            db.commit()
            logger.warning("Stale job %s automatically marked as failure (age=%s)", task_id, age)
    return job
