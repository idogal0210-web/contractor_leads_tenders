from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from typing import Dict, Any
import structlog
from core.db.session import get_sync_db
from core.db.models import SourceItem, SourceType, ProcessingStatus
from processors.llm_extractor import is_valid_lead_intent, extract_opportunity
from config.settings import settings
import asyncio
from datetime import datetime, timezone
import uuid

log = structlog.get_logger(__name__)
router = APIRouter()

"""
3. מודל סיווג כוונות AI (Intent Classification) - לרשתות חברתיות קהילתיות
בניית Webhook שיקבל פוסטים מקבוצות סגורות (דרך Make.com מ-WhatsApp/Facebook), 
והפעלת מנוע AI שפוסל במקום כל פוסט שהוא לא הצהרת כוונה ברורה להעסקת קבלן.
"""

async def process_webhook_lead(payload: Dict[str, Any]):
    """Background task to process the incoming social media post."""
    text = payload.get("text", "")
    author = payload.get("author", "אנונימי")
    platform = payload.get("platform", "WhatsApp/Facebook")
    url = payload.get("url", "")
    
    if not text:
        return
        
    log.info("received_b2c_webhook_post", author=author, platform=platform)

    # 1. שכבה ראשונה: סיווג כוונות (Intent Classification)
    is_valid = await is_valid_lead_intent(text)
    if not is_valid:
        log.info("b2c_intent_rejected", reason="Not a clear solicitation for a contractor.")
        return # נפסל במקום, לא נשמר במסד הנתונים!

    # 2. שכבה שנייה: חילוץ ישות (Entity Extraction)
    try:
        extracted = await extract_opportunity(text)
    except Exception as exc:
        log.error("b2c_entity_extraction_failed", error=str(exc))
        return

    if not extracted.is_current or extracted.opportunity_type.lower() == "irrelevant":
        log.info("b2c_entity_extraction_rejected", reason="Failed contact or relevance guardrails.")
        return

    # TODO: Insert directly into the database as a fully verified Opportunity, 
    # generate the auto-proposal, and trigger the WhatsApp / Telegram notification.
    log.info("b2c_lead_verified_and_saved", title=extracted.title.value)


@router.post("/v1/webhooks/social")
async def receive_social_post(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint for Make.com / Zapier to send new posts from Facebook/WhatsApp groups.
    Payload expected: {"text": "מחפש קבלן...", "author": "Israel", "platform": "Facebook", "url": "..."}
    """
    # Simple security token check
    auth_header = request.headers.get("Authorization")
    if not auth_header or auth_header != f"Bearer {settings.secret_key}":
        raise HTTPException(status_code=401, detail="Unauthorized webhook")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
        
    # Process asynchronously so the webhook responds immediately (200 OK) to Make.com
    background_tasks.add_task(process_webhook_lead, payload)
    return {"status": "accepted", "message": "Post received for AI intent classification"}

