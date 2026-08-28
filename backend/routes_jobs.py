"""PROMPT 5: Arka plan iş durumu sorgulama + AI üretimini asenkron tetikleyen uçlar
(/api/v1/jobs/*). Mevcut senkron /api/mealplan/generate, /api/workout/program/generate,
/api/insights/generate uçları DEĞİŞMEDEN kalır - bunlar aynı işin YENİ, bloklamayan
alternatifleridir (frontend kademeli olarak geçebilir)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import auth
import job_service
import models
from database import get_db

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


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
