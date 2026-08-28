"""
Zamanlanmış görevler (PROMPT 5 & 9): günlük check-in, haftalık analiz ve
hareketsizlik hatırlatmaları. APScheduler BackgroundScheduler kullanılır -
FastAPI süreci içinde çalışır ve `shutdown()` ile düzgünce (graceful) durur.

NOT: Şu an tüm kullanıcılara TEK bir global saatte (UTC) tetiklenir. Kullanıcı
bazlı saat dilimi/quiet-hours filtresi `notification_service.dispatch_to_user`
içinde uygulanır. Gerçek üretimde her kullanıcı için ayrı cron / Celery Beat
per-user scheduling'e geçilmesi önerilir (NotificationSettings.timezone alanı
bu geleceğe hazırlıktır)."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler = None


def _job_daily_checkin():
    from tasks import batch_send_scheduled_reminders_task
    batch_send_scheduled_reminders_task.delay("daily_checkin", "Günaydın! ☀️", "Bugünkü enerji/uyku check-in'ini yapmayı unutma.")


def _job_weekly_report():
    from tasks import batch_send_scheduled_reminders_task
    batch_send_scheduled_reminders_task.delay("weekly_report", "Haftalık analiz zamanı", "Bu haftanın koçluk raporu için dashboard'a göz at.")


def _job_inactivity_check():
    """3+ gün antrenman/beslenme kaydı olmayan kullanıcılara re-engagement bildirimi."""
    import datetime
    import models
    from database import SessionLocal
    from tasks import send_push_notification_task

    db = SessionLocal()
    try:
        cutoff = datetime.date.today() - datetime.timedelta(days=3)
        users = db.query(models.User).filter(models.User.is_active == True).all()  # noqa: E712
        for user in users:
            recent_nutrition = db.query(models.NutritionLog).filter(
                models.NutritionLog.user_id == user.id, models.NutritionLog.date >= cutoff
            ).first()
            recent_workout = db.query(models.WorkoutLog).filter(
                models.WorkoutLog.user_id == user.id, models.WorkoutLog.date >= cutoff
            ).first()
            if not recent_nutrition and not recent_workout:
                send_push_notification_task.delay(
                    user.id, "inactivity", "Seni özledik 👋",
                    "3 gündür antrenman/beslenme kaydın yok. Jarvis'e dönüp devam edelim mi?",
                )
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(_job_daily_checkin, CronTrigger(hour=6, minute=0), id="daily_checkin", replace_existing=True)  # ~09:00 TR
    _scheduler.add_job(_job_weekly_report, CronTrigger(day_of_week="mon", hour=6, minute=0), id="weekly_report", replace_existing=True)
    _scheduler.add_job(_job_inactivity_check, CronTrigger(hour=18, minute=0), id="inactivity_check", replace_existing=True)
    _scheduler.start()
    logger.info("APScheduler başlatıldı (daily_checkin, weekly_report, inactivity_check).")
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("APScheduler düzgünce durduruldu.")
