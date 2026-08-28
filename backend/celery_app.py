"""
Celery uygulaması (PROMPT 5). REDIS_URL tanımlıysa gerçek asenkron worker'lar
üzerinden çalışır (`celery -A celery_app worker`). Tanımlı değilse görevler
`task_always_eager=True` ile İSTEK SÜRECİ İÇİNDE senkron çalışır - böylece Redis
kurulu olmayan bir geliştirme ortamında da API hiçbir zaman kilitlenmez/çökmez,
sadece gerçek arka plan işleme avantajını kaybeder (bkz. README/DEPLOY notları)."""
import logging

from celery import Celery

from config import settings

logger = logging.getLogger(__name__)

_broker_url = settings.REDIS_URL or "memory://"
_result_backend = settings.REDIS_URL or "cache+memory://"
_eager = settings.CELERY_TASK_ALWAYS_EAGER or not settings.REDIS_URL

if _eager:
    logger.info("REDIS_URL tanımlı değil - Celery görevleri EAGER modda (senkron, istek içinde) çalışacak.")

celery_app = Celery("lumiere", broker=_broker_url, backend=_result_backend)

celery_app.conf.update(
    task_always_eager=_eager,
    task_eager_propagates=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=60 * 60 * 24,  # 24 saat sonra sonuçlar expire olur (PROMPT 5 kısıtı)
    task_routes={
        "tasks.analyze_video_task": {"queue": "high"},
        "tasks.analyze_food_photo_task": {"queue": "medium"},
        "tasks.generate_ai_meal_plan_task": {"queue": "medium"},
        "tasks.generate_ai_workout_program_task": {"queue": "medium"},
        "tasks.weekly_analysis_report_task": {"queue": "low"},
        "tasks.send_email_notification_task": {"queue": "high"},
        "tasks.send_push_notification_task": {"queue": "high"},
        "tasks.batch_send_scheduled_reminders_task": {"queue": "low"},
        "tasks.export_user_data_task": {"queue": "low"},
        "tasks.delete_account_task": {"queue": "low"},
    },
)
