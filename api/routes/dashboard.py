"""
api/routes/dashboard.py — מסך בדיקה מהירה (Quick Review Dashboard) ב-FastAPI ו-HTMX.

מספק תצוגה מרוכזת של:
1. לידים ומכרזים חדשים לטיפול מידי (ממוינים לפי ציון התאמה + Fast-Track).
2. מכרזים פעילים עם תאריכי יעד מתקרבים.
3. דוחות יומיים שמורים.
4. טופס הדבקה ידנית מהירה של לידים (וואטסאפ/פייסבוק).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from core.db.session import get_sync_db
from core.db.models import Opportunity, MatchStatus, ActionType, OpportunityAction
from reports.daily_report import REPORT_BASE_DIR

router = APIRouter()
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
def get_dashboard(request: Request, db: Session = Depends(get_sync_db)):
    """דף הבית של מסך הבדיקה המהירה."""
    # 1. שליפת הזדמנויות אחרונות (עד 25)
    recent_opportunities = (
        db.query(Opportunity)
        .order_by(Opportunity.is_fast_track.desc(), Opportunity.score_business_fit.desc().nullslast())
        .limit(25)
        .all()
    )

    # 2. שליפת מכרזים פעילים עם מועד הגשה עתידי
    now = datetime.now(timezone.utc)
    active_tenders = (
        db.query(Opportunity)
        .filter(
            Opportunity.opportunity_type == "tender",
            Opportunity.deadline_value >= now,
        )
        .order_by(Opportunity.deadline_value.asc())
        .limit(10)
        .all()
    )

    # 3. סטטיסטיקות מהירות
    total_count = db.query(Opportunity).count()
    fast_track_count = db.query(Opportunity).filter(Opportunity.is_fast_track == True).count()
    fit_count = db.query(Opportunity).filter(Opportunity.match_status == MatchStatus.FIT).count()

    # 4. רשימת דוחות שמורים
    saved_reports = []
    if REPORT_BASE_DIR.exists():
        saved_reports = sorted([p.name for p in REPORT_BASE_DIR.iterdir() if p.is_dir()], reverse=True)[:5]

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "opportunities": recent_opportunities,
            "active_tenders": active_tenders,
            "stats": {
                "total": total_count,
                "fast_track": fast_track_count,
                "fit": fit_count,
            },
            "saved_reports": saved_reports,
        },
    )


@router.get("/opportunity/{opportunity_id}", response_class=HTMLResponse)
def get_opportunity_page(
    request: Request,
    opportunity_id: str,
    db: Session = Depends(get_sync_db),
):
    """דף פירוט מלא להזדמנות ספציפית."""
    try:
        opp_uuid = uuid.UUID(opportunity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID")

    item = db.query(Opportunity).filter(Opportunity.id == opp_uuid).first()
    if not item:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    return templates.TemplateResponse(
        request=request,
        name="opportunity.html",
        context={
            "opportunity": item,
        },
    )
