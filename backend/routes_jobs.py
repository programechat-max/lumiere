"""PROMPT 5: Arka plan iş durumu sorgulama + AI üretimini asenkron tetikleyen uçlar
(/api/v1/jobs/*). Mevcut senkron /api/mealplan/generate, /api/workout/program/generate,
/api/insights/generate uçları DEĞİŞMEDEN kalır - bunlar aynı işin YENİ, bloklamayan
alternatifleridir (frontend kademeli olarak geçebilir)."""
import os
import tempfile
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

import auth
import job_service
import models
from database import get_db

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])
MAX_MEDIA_BYTES = 300 * 1024 * 1024


@router.get("/{task_id}")
def get_job_status(task_id: str, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    job = job_service.get_job(db, task_id, user_id=current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="İş bulunamadı.")
    return {
        "task_id": job.task_id, "job_type": job.job_type, "status": job.status,
        "progress_percent": job.progress_percent, "result": job.result,
        "error_message": job.error_message, "created_at": job.created_at, "completed_at": job.completed_at,
    }


@router.post("/onboarding/video")
async def queue_onboarding_video(file: UploadFile = File(...), current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Videoyu diske yazıp worker kuyruğuna bırakır; Gemini HTTP isteğini bloklamaz."""
    media = await file.read()
    if not media:
        raise HTTPException(status_code=400, detail="Boş video dosyası.")
    if len(media) > MAX_MEDIA_BYTES:
        raise HTTPException(status_code=413, detail="Video çok büyük (300MB üstü).")
    suffix = ".mp4" if "mp4" in (file.content_type or "") else ".webm"
    media_dir = os.path.join(tempfile.gettempdir(), "lumiere-media")
    os.makedirs(media_dir, exist_ok=True)
    file_path = os.path.join(media_dir, f"{uuid.uuid4().hex}{suffix}")
    with open(file_path, "wb") as target:
        target.write(media)

    from tasks import analyze_video_file_task
    task_id = uuid.uuid4().hex
    job_service.create_job(db, task_id, "analyze_onboarding_video", user_id=current_user.id)
    try:
        analyze_video_file_task.apply_async(
            args=[file_path, file.content_type or "video/webm", current_user.id], task_id=task_id
        )
    except Exception:
        try:
            os.remove(file_path)
        except OSError:
            pass
        job = job_service.get_job(db, task_id, user_id=current_user.id)
        if job:
            job.status = "failure"; job.error_message = "Worker kuyruğuna bağlanılamadı."; db.commit()
        raise HTTPException(status_code=503, detail="Video iş kuyruğu şu anda kullanılamıyor.")
    return {"task_id": task_id, "status": "pending"}


@router.post("/meal-plan/generate")
def trigger_meal_plan_async(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    from tasks import generate_ai_meal_plan_task
    async_result = generate_ai_meal_plan_task.delay(current_user.id)
    job_service.create_job(db, async_result.id, "generate_ai_meal_plan", user_id=current_user.id)
    return {"task_id": async_result.id}


@router.post("/workout-program/generate")
def trigger_workout_program_async(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    from tasks import generate_ai_workout_program_task
    async_result = generate_ai_workout_program_task.delay(current_user.id)
    job_service.create_job(db, async_result.id, "generate_ai_workout_program", user_id=current_user.id)
    return {"task_id": async_result.id}


@router.post("/weekly-analysis/generate")
def trigger_weekly_analysis_async(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    from tasks import weekly_analysis_report_task
    async_result = weekly_analysis_report_task.delay(current_user.id)
    job_service.create_job(db, async_result.id, "weekly_analysis_report", user_id=current_user.id)
    return {"task_id": async_result.id}
