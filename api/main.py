"""
api/main.py — אפליקציית FastAPI ראשית.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import uuid
import structlog
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import not_

from config.settings import settings
from core.db.session import get_sync_db
from core.db.models import Opportunity, OpportunityAction, ActionType

log = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info("startup", environment=settings.environment, debug=settings.debug)
    yield
    log.info("shutdown")

app = FastAPI(
    title="מערכת איתור לידים",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class ActionRequest(BaseModel):
    action_type: str = Field(description="action_type: rejected | permanently_deleted | restored | viewed")

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/leads")
def get_leads(db: Session = Depends(get_sync_db)):
    """returns all opportunities from the DB that are NOT permanently deleted"""
    
    # Subquery or filter out those that have a 'permanently_deleted' action
    # Alternatively, we just load all and filter if there's no status field on Opportunity.
    # The instructions say "returns all opportunities from the DB that are NOT permanently deleted."
    
    # Check if they have an action of 'permanently_deleted'
    deleted_opp_ids = db.query(OpportunityAction.opportunity_id).filter(
        OpportunityAction.action_type == ActionType.PERMANENTLY_DELETED.value
    ).subquery()

    leads = db.query(Opportunity).filter(
        Opportunity.id.not_in(deleted_opp_ids)
    ).order_by(Opportunity.created_at.desc()).all()
    
    # Provide them in a format the UI expects (which matches ui_builder.py variables)
    result = []
    for lead in leads:
        result.append({
            "id": str(lead.id),
            "title_value": lead.title_value,
            "opportunity_type": lead.opportunity_type,
            "category": lead.category,
            "work_type_value": lead.work_type_value,
            "location_value": lead.location_value,
            "budget_value": lead.budget_value,
            "deadline_value": lead.deadline_value.isoformat() if lead.deadline_value else None,
            "score_business_fit": lead.score_business_fit,
            "score_urgency": lead.score_urgency,
            "score_confidence": lead.score_confidence,
            "is_fast_track": lead.is_fast_track,
            "match_status": lead.match_status,
            "match_reason": lead.match_reason,
            "tender_number": lead.tender_number,
            "publisher_name": lead.publisher_name,
            "contact_value": lead.contact_value,
            "source_label": lead.source_label,
            "validation_status": lead.validation_status,
            "freshness_status": lead.freshness_status,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
        })
    return result

@app.post("/api/leads/{opp_id}/action")
def record_action(opp_id: str, payload: ActionRequest, db: Session = Depends(get_sync_db)):
    """accepts {"action_type": "rejected" | "permanently_deleted" | "restored" | "viewed"}"""
    try:
        opp_uuid = uuid.UUID(opp_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")

    opp = db.query(Opportunity).filter(Opportunity.id == opp_uuid).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    try:
        action_enum = ActionType(payload.action_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid action type")

    action = OpportunityAction(
        id=uuid.uuid4(),
        opportunity_id=opp_uuid,
        action_type=action_enum,
    )
    db.add(action)

    # Optional: Update the match_status or a local field if needed
    if action_enum == ActionType.REJECTED:
        opp.match_status = "no_fit"
    
    db.commit()
    return {"status": "ok"}

# Keep the remaining routes if they exist
try:
    from api.routes import webhooks, dashboard, reports
    app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
    app.include_router(dashboard.router, prefix="", tags=["dashboard"])
    app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
except ImportError:
    pass

