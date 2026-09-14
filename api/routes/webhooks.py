"""
api/routes/webhooks.py — קליטת פריטים והודעות ממקורות חיצוניים ומ-Webhooks.

תומך בקליטת לידים בהדבקה ידנית (למשל מוואטסאפ או פייסבוק) וקליטת Webhooks מנוטרים.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
import structlog

from core.queue.tasks import process_webhook_item

log = structlog.get_logger(__name__)
router = APIRouter()


class InboundLeadPayload(BaseModel):
    """מודל לקליטת ליד ידני או הודעת Webhook חיצונית."""
    content: str = Field(description="טקסט ההודעה או הפנייה")
    source_label: str = Field(default="הדבקה ידנית", description="שם המקור או תגית")
    url: Optional[str] = Field(default=None, description="קישור לפוסט/אתר אם קיים")
    contact_phone: Optional[str] = Field(default=None, description="טלפון אם ידוע מראש")


@router.post("/external", status_code=202)
async def receive_external_webhook(
    payload: InboundLeadPayload,
    background_tasks: BackgroundTasks,
):
    """קבלת פריט מ-Webhook חיצוני ושליחתו לתור העיבוד (Celery / BackgroundTask)."""
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="content cannot be empty")

    log.info("inbound_webhook_received", source=payload.source_label, length=len(payload.content))

    # הפעלה במקביל
    try:
        process_webhook_item.delay(
            raw_content=payload.content,
            source_id="manual_webhook",
            url=payload.url,
        )
    except Exception as exc:
        log.warning("celery_delay_failed_fallback_to_direct", error=str(exc))
        # אם Redis/Celery אינם רצים בסביבת פיתוח מקומית, נריץ ישירות ב-background_tasks
        background_tasks.add_task(
            process_webhook_item,
            raw_content=payload.content,
            source_id="manual_webhook",
            url=payload.url,
        )

    return {
        "status": "accepted",
        "message": "הפנייה התקבלה בהצלחה ונשלחה לעיבוד, סיווג וניקוד",
        "source": payload.source_label,
    }


@router.post("/manual-lead", status_code=202)
async def submit_manual_lead(
    payload: InboundLeadPayload,
    background_tasks: BackgroundTasks,
):
    """נקודת קצה ייעודית למסך בדיקה מהירה — להדבקת הודעות וואטסאפ או פייסבוק."""
    return await receive_external_webhook(payload, background_tasks)
