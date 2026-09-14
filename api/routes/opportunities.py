"""
api/routes/opportunities.py — ניהול ופעולות על הזדמנויות עסקיות (Leads & Tenders).

מספק CRUD, עדכון סטטוס אנושי (reviewed, contacted, submitted, won, rejected),
פילטור לפי ניקוד ומסלול מהיר.
"""
from __future__ import annotations

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import structlog

from core.db.session import get_sync_db
from core.db.models import (
    Opportunity, OpportunityAction, ActionType, MatchStatus, OpportunityCategory
)

log = structlog.get_logger(__name__)
router = APIRouter()


class ActionRequest(BaseModel):
    action_type: ActionType = Field(description="סוג הפעולה: reviewed, contacted, submitted, won, lost, rejected")
    notes: Optional[str] = Field(default=None, description="הערות אישיות של הקבלן")
    acted_by: Optional[str] = Field(default="קבלן", description="שם המשתמש המבצע")


class UpdateMatchStatusRequest(BaseModel):
    match_status: MatchStatus
    reason: Optional[str] = None


@router.get("/")
def list_opportunities(
    match_status: Optional[MatchStatus] = None,
    category: Optional[OpportunityCategory] = None,
    is_fast_track: Optional[bool] = None,
    opportunity_type: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_sync_db),
):
    """שליפת רשימת הזדמנויות עם סינונים מתקדמים ופגינציה."""
    query = db.query(Opportunity)

    if match_status:
        query = query.filter(Opportunity.match_status == match_status)
    if category:
        query = query.filter(Opportunity.category == category)
    if is_fast_track is not None:
        query = query.filter(Opportunity.is_fast_track == is_fast_track)
    if opportunity_type:
        query = query.filter(Opportunity.opportunity_type == opportunity_type)

    total = query.count()
    items = (
        query.order_by(Opportunity.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": str(item.id),
                "title": item.title_value,
                "opportunity_type": item.opportunity_type,
                "category": item.category,
                "work_type": item.work_type_value,
                "location": item.location_value,
                "budget": item.budget_value,
                "deadline": item.deadline_value.isoformat() if item.deadline_value else None,
                "score_business_fit": item.score_business_fit,
                "score_urgency": item.score_urgency,
                "score_confidence": item.score_confidence,
                "is_fast_track": item.is_fast_track,
                "match_status": item.match_status.value if item.match_status else None,
                "match_reason": item.match_reason,
                "tender_number": item.tender_number,
                "publisher_name": item.publisher_name,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ],
    }


@router.get("/{opportunity_id}")
def get_opportunity(opportunity_id: str, db: Session = Depends(get_sync_db)):
    """שליפת פרטי הזדמנות בודדת כולל ראיות, אירועים ופעולות שננקטו."""
    try:
        opp_uuid = uuid.UUID(opportunity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    item = db.query(Opportunity).filter(Opportunity.id == opp_uuid).first()
    if not item:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    return {
        "id": str(item.id),
        "title": {
            "value": item.title_value,
            "evidence": item.title_evidence,
            "confidence": item.title_confidence,
        },
        "location": {
            "value": item.location_value,
            "evidence": item.location_evidence,
            "confidence": item.location_confidence,
        },
        "work_type": {
            "value": item.work_type_value,
            "evidence": item.work_type_evidence,
            "confidence": item.work_type_confidence,
        },
        "budget": {
            "value": item.budget_value,
            "currency": item.budget_currency,
            "evidence": item.budget_evidence,
            "confidence": item.budget_confidence,
        },
        "deadline": {
            "value": item.deadline_value.isoformat() if item.deadline_value else None,
            "evidence": item.deadline_evidence,
            "confidence": item.deadline_confidence,
        },
        "contact": {
            "value": item.contact_value,
            "evidence": item.contact_evidence,
            "confidence": item.contact_confidence,
        },
        "scores": {
            "business_fit": item.score_business_fit,
            "urgency": item.score_urgency,
            "confidence": item.score_confidence,
            "is_fast_track": item.is_fast_track,
        },
        "match": {
            "status": item.match_status.value if item.match_status else None,
            "reason": item.match_reason,
        },
        "tender_number": item.tender_number,
        "publisher_name": item.publisher_name,
        "tender_events": [
            {
                "id": str(ev.id),
                "event_type": ev.event_type,
                "event_date": ev.event_date.isoformat() if ev.event_date else None,
                "notes": ev.notes,
            }
            for ev in (item.tender_events or [])
        ],
        "actions": [
            {
                "id": str(act.id),
                "action_type": act.action_type.value,
                "notes": act.notes,
                "acted_by": act.acted_by,
                "acted_at": act.acted_at.isoformat() if act.acted_at else None,
            }
            for act in (item.actions or [])
        ],
    }


@router.post("/{opportunity_id}/action")
def record_action(
    opportunity_id: str,
    payload: ActionRequest,
    db: Session = Depends(get_sync_db),
):
    """תיעוד פעולה אנושית (קבלן בדק, יצר קשר, הגיש הצעה, זכה, פסל)."""
    try:
        opp_uuid = uuid.UUID(opportunity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    item = db.query(Opportunity).filter(Opportunity.id == opp_uuid).first()
    if not item:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    action = OpportunityAction(
        id=uuid.uuid4(),
        opportunity_id=opp_uuid,
        action_type=payload.action_type,
        notes=payload.notes,
        acted_by=payload.acted_by,
    )
    db.add(action)
    db.commit()

    log.info("opportunity_action_recorded", opp_id=opportunity_id, action=payload.action_type.value)
    return {"status": "ok", "message": f"פעולה '{payload.action_type.value}' תועדה בהצלחה"}


@router.post("/{opportunity_id}/dismiss")
def dismiss_opportunity(opportunity_id: str, db: Session = Depends(get_sync_db)):
    """דחייה מהירה של הזדמנות (פסילה)."""
    action_req = ActionRequest(action_type=ActionType.REJECTED, notes="נדחה במהירות מהדשבורד")
    return record_action(opportunity_id=opportunity_id, payload=action_req, db=db)
