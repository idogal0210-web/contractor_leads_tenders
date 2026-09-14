"""
reports/daily_report.py — הפקה, שמירה מקומית והפצה של דוח יומי מסכם.

1. מפיק נתונים על כל ההזדמנויות שאותרו ביממה האחרונה.
2. שומר עותק מקומי (JSON + HTML) בתיקיית reports/output/<date>/.
3. שולח אימייל + תקציר טלגרם.
4. נתונים אלו מוצגים גם בדשבורד עם תאריך הפקה.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy.orm import Session

from config.settings import settings
from core.db.models import Opportunity, TenderEvent, MatchStatus
from notifications.email_sender import send_daily_report_email
from notifications.telegram_sender import send_daily_report_telegram

log = structlog.get_logger(__name__)

REPORT_BASE_DIR = Path(__file__).parent / "output"


def generate_daily_report_data(db: Session, target_date: date | None = None) -> dict[str, Any]:
    """שליפת וארגון נתוני הדוח עבור תאריך נתון (ברירת מחדל: היום)."""
    if target_date is None:
        target_date = datetime.now(timezone.utc).date()

    start_of_day = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_of_day = start_of_day + timedelta(days=1)

    # 1. שליפת כל ההזדמנויות שנוצרו באותו יום
    opportunities = (
        db.query(Opportunity)
        .filter(Opportunity.created_at >= start_of_day, Opportunity.created_at < end_of_day)
        .order_by(Opportunity.score_business_fit.desc().nullslast())
        .all()
    )

    total_discovered = len(opportunities)
    fit_count = sum(1 for o in opportunities if o.match_status == MatchStatus.FIT)
    fast_track_count = sum(1 for o in opportunities if o.is_fast_track)
    needs_review_count = sum(1 for o in opportunities if o.match_status == MatchStatus.NEEDS_REVIEW)

    opp_list = [
        {
            "id": str(o.id),
            "title": o.title_value or "ללא כותרת",
            "opportunity_type": o.opportunity_type,
            "work_type": o.work_type_value or "כללי",
            "location": o.location_value or "ארצי",
            "budget": o.budget_value,
            "score": o.score_business_fit or 0,
            "is_fast_track": o.is_fast_track,
            "match_status": o.match_status.value if o.match_status else "needs_review",
            "tender_number": o.tender_number,
        }
        for o in opportunities
    ]

    # 2. מועדי הגשה קרובים (7 ימים הבאים)
    upcoming_limit = datetime.now(timezone.utc) + timedelta(days=7)
    upcoming_events = (
        db.query(Opportunity)
        .filter(
            Opportunity.deadline_value >= datetime.now(timezone.utc),
            Opportunity.deadline_value <= upcoming_limit,
        )
        .order_by(Opportunity.deadline_value.asc())
        .limit(10)
        .all()
    )

    upcoming_deadlines = [
        {
            "id": str(u.id),
            "title": u.title_value or "מכרז",
            "tender_number": u.tender_number,
            "deadline": u.deadline_value.strftime("%d/%m/%Y %H:%M") if u.deadline_value else "-",
            "publisher": u.publisher_name,
        }
        for u in upcoming_events
    ]

    report_payload = {
        "date": target_date.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "total_discovered": total_discovered,
            "fit_count": fit_count,
            "fast_track_count": fast_track_count,
            "needs_review_count": needs_review_count,
        },
        "opportunities": opp_list,
        "upcoming_deadlines": upcoming_deadlines,
    }

    return report_payload


def save_report_locally(report_data: dict[str, Any]) -> Path:
    """שמירת עותק מקומי של הדוח בקבצי JSON ו-HTML."""
    date_str = report_data["date"]
    out_dir = REPORT_BASE_DIR / date_str
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    # רינדור ושמירת HTML
    from jinja2 import Environment, FileSystemLoader
    templates_dir = Path(__file__).parent.parent / "notifications" / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)
    tpl = env.get_template("daily_report.html")
    rendered_html = tpl.render(report=report_data)

    html_path = out_dir / "report.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)

    log.info("report_saved_locally", dir=str(out_dir))
    return out_dir


async def generate_and_send(db: Session | None = None) -> dict[str, Any]:
    """
    נקודת הכניסה הראשית להפקת והפצת הדוח היומי.
    מופעלת מ-Celery Beat או ידנית מה-API.
    """
    should_close_db = False
    if db is None:
        from core.db.session import get_sync_db
        db = next(get_sync_db())
        should_close_db = True

    try:
        report_data = generate_daily_report_data(db)
        save_report_locally(report_data)

        # שליחה במייל
        recipient = settings.smtp_from or settings.smtp_user
        if recipient:
            await send_daily_report_email(report_data, recipient_email=recipient)

        # שליחת תקציר לטלגרם
        stats = report_data["stats"]
        summary = (
            f"📅 תאריך: {report_data['date']}\n"
            f"📥 אותרו: {stats['total_discovered']} | 🎯 מתאימים: {stats['fit_count']}\n"
            f"🔴 מסלול מהיר: {stats['fast_track_count']} | 🔍 לבדיקה: {stats['needs_review_count']}"
        )
        await send_daily_report_telegram(summary)

        log.info("daily_report_pipeline_completed", date=report_data["date"])
        return report_data

    finally:
        if should_close_db:
            db.close()
