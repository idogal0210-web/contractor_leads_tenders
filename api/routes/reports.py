"""
api/routes/reports.py — נקודות קצה להצגה והפקה של דוחות יומיים מסכמים.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from core.db.session import get_sync_db
from reports.daily_report import (
    generate_daily_report_data,
    generate_and_send,
    REPORT_BASE_DIR,
)

router = APIRouter()


@router.get("/daily")
def get_daily_report(
    report_date: Optional[str] = Query(default=None, description="תאריך בפורמט YYYY-MM-DD"),
    db: Session = Depends(get_sync_db),
):
    """שליפת נתוני דוח יומי ב-JSON."""
    target_d = None
    if report_date:
        try:
            target_d = datetime.strptime(report_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")

    return generate_daily_report_data(db, target_date=target_d)


@router.get("/daily/{report_date}/html", response_class=HTMLResponse)
def get_daily_report_html(report_date: str):
    """צפייה בעותק ה-HTML השמור של הדוח."""
    html_file = REPORT_BASE_DIR / report_date / "report.html"
    if not html_file.exists():
        raise HTTPException(status_code=404, detail="HTML report not found for this date")

    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@router.post("/daily/generate")
async def trigger_generate_report(db: Session = Depends(get_sync_db)):
    """הפקה מיידית של הדוח היומי ושליחתו במייל ובטלגרם."""
    report = await generate_and_send(db=db)
    return {
        "status": "success",
        "message": "דוח יומי הופק, נשמר מקומית והופץ בהצלחה",
        "date": report["date"],
        "stats": report["stats"],
    }


@router.get("/list")
def list_saved_reports():
    """רשימת כל הדוחות השמורים בדיסק מקומית."""
    if not REPORT_BASE_DIR.exists():
        return {"reports": []}

    dates = [p.name for p in REPORT_BASE_DIR.iterdir() if p.is_dir()]
    dates.sort(reverse=True)
    return {"reports": dates}
