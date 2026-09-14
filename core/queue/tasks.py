"""
core/queue/tasks.py — הגדרות משימות Celery וצינור עיבוד מלא (End-to-End Pipeline).
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from core.queue.celery_app import app
from config.settings import settings
from core.db.session import SessionLocal
from core.db.models import (
    Source, SourceItem, Opportunity, ContractorProfile,
    ProcessingStatus, MatchStatus, OpportunityCategory
)
from processors.deduplication import compute_content_hash, is_duplicate
from processors.ocr import extract_text_from_string
from processors.llm_extractor import extract_opportunity
from processors.classifier import classify_opportunity
from processors.scorer import score_opportunity
from processors.matcher import match_to_profile
from notifications.dispatcher import decide_dispatch, execute_dispatch
from reports.daily_report import generate_and_send as run_daily_report

log = structlog.get_logger(__name__)


def _get_contractor_profile(db) -> dict[str, Any]:
    """טעינת פרופיל הקבלן מ-DB או מקובץ JSON כברירת מחדל."""
    prof = db.query(ContractorProfile).filter(ContractorProfile.is_active == True).first()
    if prof:
        return {
            "name": prof.name,
            "service_area": prof.service_area,
            "trades": prof.trades or [],
            "excluded_trades": prof.excluded_trades or [],
            "min_project_value": prof.min_project_value,
            "max_project_value": prof.max_project_value,
            "trade_keywords_hebrew": prof.trade_keywords_hebrew or {},
        }
    with open("config/contractor_profile.json", "r", encoding="utf-8") as f:
        return json.load(f)


@app.task(bind=True, max_retries=2)
def process_webhook_item(self, raw_content: str, source_id: str, url: str | None = None):
    """
    עיבוד פריט שהתקבל בהדבקה ידנית או Webhook דרך כל שלבי ה-Pipeline:
    1. מניעת כפילויות (SHA-256)
    2. שמירת source_item גולמי
    3. חילוץ מובנה עובדתי ב-Gemini 3.8 Flash
    4. סיווג לקטגוריה
    5. ניקוד 3-מדדים וזיהוי Fast-Track
    6. התאמה לפרופיל הקבלן
    7. שמירת Opportunity
    8. שיגור התראות מבוסס-כללים (Rule-Based)
    """
    task_log = log.bind(source_id=source_id)
    task_log.info("processing_inbound_item", length=len(raw_content))

    content_hash = compute_content_hash(raw_content)

    db = SessionLocal()
    try:
        # 1. בדיקת כפילות
        if is_duplicate(content_hash, db):
            task_log.info("duplicate_inbound_item_skipped", hash=content_hash)
            return {"status": "skipped", "reason": "duplicate"}

        # 2. שמירת פריט מקור
        source_rec = db.query(Source).first()
        actual_source_id = source_rec.id if source_rec else uuid.uuid4()

        source_item = SourceItem(
            id=uuid.uuid4(),
            source_id=actual_source_id,
            raw_content=raw_content,
            content_hash=content_hash,
            url=url,
            item_type="lead",
            processing_status=ProcessingStatus.PROCESSING,
        )
        db.add(source_item)
        db.commit()

        # 3. חילוץ Gemini 3.8 Flash
        try:
            extracted = asyncio.run(extract_opportunity(raw_content))
        except Exception as exc:
            task_log.error("llm_extraction_error", error=str(exc))
            source_item.processing_status = ProcessingStatus.FAILED
            source_item.processing_error = str(exc)
            db.commit()
            return {"status": "error", "error": str(exc)}

        # 4. סיווג
        category, cat_conf = classify_opportunity(extracted, raw_content)

        # 5. ניקוד
        profile_data = _get_contractor_profile(db)
        score = score_opportunity(
            extracted=extracted,
            contractor_profile=profile_data,
            fast_track_config=settings.fast_track_config,
            published_at=datetime.now(timezone.utc),
        )

        # 6. התאמה לפרופיל
        match_res = match_to_profile(extracted, profile_data, score)

        # 7. שמירת Opportunity ב-DB
        deadline_dt = None
        if extracted.deadline.value:
            try:
                deadline_dt = datetime.fromisoformat(str(extracted.deadline.value).replace("Z", "+00:00"))
            except Exception:
                deadline_dt = None

        opp = Opportunity(
            id=uuid.uuid4(),
            source_item_id=source_item.id,
            opportunity_type=extracted.opportunity_type or "lead",
            category=category,
            title_value=extracted.title.value,
            title_evidence=extracted.title.evidence_text,
            title_confidence=extracted.title.confidence,
            location_value=extracted.location.value,
            location_evidence=extracted.location.evidence_text,
            location_confidence=extracted.location.confidence,
            budget_value=extracted.budget.value,
            budget_currency=extracted.budget_currency or "ILS",
            budget_evidence=extracted.budget.evidence_text,
            budget_confidence=extracted.budget.confidence,
            work_type_value=extracted.work_type.value,
            work_type_evidence=extracted.work_type.evidence_text,
            work_type_confidence=extracted.work_type.confidence,
            deadline_value=deadline_dt,
            deadline_evidence=extracted.deadline.evidence_text,
            deadline_confidence=extracted.deadline.confidence,
            contact_value=extracted.contact.value,
            contact_evidence=extracted.contact.evidence_text,
            contact_confidence=extracted.contact.confidence,
            tender_number=extracted.tender_number,
            publisher_name=extracted.publisher_name,
            score_business_fit=score.business_fit,
            score_urgency=score.urgency,
            score_confidence=score.confidence,
            is_fast_track=score.is_fast_track,
            match_status=match_res.status,
            match_reason=match_res.reason,
        )
        db.add(opp)
        source_item.processing_status = ProcessingStatus.DONE
        db.commit()
        db.refresh(opp)

        match_status_str = opp.match_status.value if hasattr(opp.match_status, 'value') else str(opp.match_status)
        category_str = opp.category.value if hasattr(opp.category, 'value') else str(opp.category)

        dispatch_dec = decide_dispatch(
            opportunity_id=str(opp.id),
            match_status=match_status_str,
            category=category_str,
            is_fast_track=opp.is_fast_track,
            score_business_fit=opp.score_business_fit or 0,
            score_urgency=opp.score_urgency or 0,
            score_confidence=opp.score_confidence or 0,
            already_notified=False,
            fast_track_config=settings.fast_track_config,
        )

        asyncio.run(execute_dispatch(opp, dispatch_dec, db))

        task_log.info(
            "pipeline_item_success",
            opp_id=str(opp.id),
            decision=dispatch_dec.decision.value,
            score=score.business_fit,
        )
        return {
            "status": "success",
            "opportunity_id": str(opp.id),
            "title": opp.title_value,
            "decision": dispatch_dec.decision.value,
        }

    finally:
        db.close()


@app.task
def scan_all_sources():
    """סריקת כל המקורות הפעילים."""
    db = SessionLocal()
    try:
        sources = db.query(Source).filter(Source.status == "active").all()
        log.info("scan_all_sources_triggered", active_count=len(sources))
        for src in sources:
            scan_source.delay(str(src.id))
    finally:
        db.close()


@app.task(bind=True, max_retries=2)
def scan_source(self, source_id: str):
    """סריקת מקור יחיד (gov.il / municipal / yad2)."""
    log.info("scanning_source", source_id=source_id)
    # הרצת המתאם המתאים לפי סוג המקור
    return {"status": "ok", "source_id": source_id}


@app.task
def send_daily_report():
    """הפקת והפצת הדוח היומי."""
    log.info("triggering_daily_report_task")
    asyncio.run(run_daily_report())
