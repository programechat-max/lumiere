"""
Arka plan iş takibi (PROMPT 5): her Celery görevi için ilerleme/durum bilgisini
veritabanına (JobStatus) yazar - frontend `/api/v1/jobs/{task_id}` ile polling
yapabilir."""
from typing import Optional

from sqlalchemy.orm import Session

import models
from database import SessionLocal


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
        if status in ("success", "failure"):
            job.completed_at = datetime.datetime.utcnow()
        db.commit()
    finally:
        db.close()


def get_job(db: Session, task_id: str, user_id: Optional[int] = None) -> Optional[models.JobStatus]:
    query = db.query(models.JobStatus).filter(models.JobStatus.task_id == task_id)
    if user_id is not None:
        query = query.filter(models.JobStatus.user_id == user_id)
    return query.first()
