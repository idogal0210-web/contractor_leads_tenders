"""
core/queue/celery_app.py
------------------------
הגדרת אפליקציית Celery המרכזית עם תזמון Beat ותצורת עובדים.
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from config.settings import settings

# ---------------------------------------------------------------------------
# אתחול האפליקציה
# ---------------------------------------------------------------------------

app = Celery("leads_tenders")

app.config_from_object(
    {
        # ---------------------------------------------------------------
        # חיבורים
        # ---------------------------------------------------------------
        "broker_url": settings.redis_url,
        "result_backend": settings.redis_url,
        # ---------------------------------------------------------------
        # סריאליזציה
        # ---------------------------------------------------------------
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        # ---------------------------------------------------------------
        # שעון-זמן
        # ---------------------------------------------------------------
        "timezone": "Asia/Jerusalem",
        "enable_utc": True,
        # ---------------------------------------------------------------
        # ביצועי עובד
        # ---------------------------------------------------------------
        "worker_concurrency": 4,
        "task_soft_time_limit": 300,   # שניות — Soft Kill
        "task_time_limit": 600,        # שניות — Hard Kill
        # ---------------------------------------------------------------
        # אמינות
        # ---------------------------------------------------------------
        "task_acks_late": True,
        "task_reject_on_worker_lost": True,
        "task_track_started": True,
        "worker_prefetch_multiplier": 1,
        # ---------------------------------------------------------------
        # תזמון Beat — שלוש סריקות יומיות
        # ---------------------------------------------------------------
        "beat_schedule": {
            # סריקת בוקר — 06:00
            "scan-all-sources-morning": {
                "task": "core.queue.tasks.scan_all_sources",
                "schedule": crontab(hour=6, minute=0),
                "options": {"queue": "scans"},
            },
            # סריקת צהריים — 12:00
            "scan-all-sources-noon": {
                "task": "core.queue.tasks.scan_all_sources",
                "schedule": crontab(hour=12, minute=0),
                "options": {"queue": "scans"},
            },
            # סריקת ערב — 18:00
            "scan-all-sources-evening": {
                "task": "core.queue.tasks.scan_all_sources",
                "schedule": crontab(hour=18, minute=0),
                "options": {"queue": "scans"},
            },
            # דוח יומי — 20:00
            "send-daily-report": {
                "task": "core.queue.tasks.send_daily_report",
                "schedule": crontab(hour=20, minute=0),
                "options": {"queue": "reports"},
            },
        },
        # ---------------------------------------------------------------
        # תורים
        # ---------------------------------------------------------------
        "task_default_queue": "default",
        "task_queues": {
            "default": {},
            "scans": {},
            "reports": {},
            "webhooks": {},
        },
        # ---------------------------------------------------------------
        # ניטור
        # ---------------------------------------------------------------
        "worker_send_task_events": True,
        "task_send_sent_event": True,
    }
)

# גילוי אוטומטי של משימות בחבילות הפרויקט
app.autodiscover_tasks(
    [
        "core.queue",
    ]
)
