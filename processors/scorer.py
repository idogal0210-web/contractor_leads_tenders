"""
processors/scorer.py — ניקוד רב-ממדי (3 מדדים נפרדים) וזיהוי מסלול מהיר (Fast-Track).

מדדי הניקוד (0-100):
1. business_fit: התאמה עסקית (מקצועות, מיקום גיאוגרפי, גודל עבודה/תקציב).
2. urgency: דחיפות וטריות (מועד פרסום לעומת תאריך יעד/ביצוע).
3. confidence: ביטחון בחילוץ (רמת הוודאות של המידע המחולץ).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from processors.llm_extractor import ExtractedOpportunity


@dataclass
class OpportunityScore:
    """תוצאת ניקוד ההזדמנות העסקית."""
    business_fit: int
    urgency: int
    confidence: int
    is_fast_track: bool
    score_reasons: dict[str, Any]


def score_opportunity(
    extracted: ExtractedOpportunity,
    contractor_profile: dict[str, Any],
    fast_track_config: dict[str, Any],
    published_at: datetime | None = None,
) -> OpportunityScore:
    """
    חישוב 3 מדדי הניקוד וקביעת זכאות למסלול מהיר (Fast-Track).
    """
    reasons: dict[str, Any] = {}

    # -------------------------------------------------------------------------
    # 1. התאמה עסקית (business_fit) — 0 עד 100
    # -------------------------------------------------------------------------
    trade_score = 0
    trade_reasons = []
    work_val = (extracted.work_type.value or "").lower()
    title_val = (extracted.title.value or "").lower()
    full_val = f"{work_val} {title_val}"

    # בדיקת מילות מפתח כנגד מקצועות הקבלן
    keyword_map = contractor_profile.get("trade_keywords_hebrew", {})
    matched_trades = []

    for trade_name, keywords in keyword_map.items():
        for kw in keywords:
            if kw.lower() in full_val:
                matched_trades.append(trade_name)
                break

    if matched_trades:
        trade_score = 60
        trade_reasons.append(f"התאמה למקצועות: {', '.join(set(matched_trades))}")
    else:
        # התאמה כללית אם יש מונח בנייה
        if any(term in full_val for term in ["בנייה", "שיפוץ", "עבודה", "פרויקט"]):
            trade_score = 35
            trade_reasons.append("התאמה לענף כללי")
        else:
            trade_score = 10
            trade_reasons.append("אין התאמה מובהקת למקצוע")

    # התאמת מיקום — שירות ארצי שווה 40 נקודות מלאות
    location_score = 40
    trade_reasons.append("אזור שירות ארצי — התאמה מלאה לכל הארץ")

    # בדיקת גודל פרויקט / תקציב (אם הוגדר מינימום/מקסימום)
    budget_val = extracted.budget.value
    if budget_val is not None:
        try:
            val = float(budget_val)
            min_val = contractor_profile.get("min_project_value")
            max_val = contractor_profile.get("max_project_value")

            if min_val is not None and val < min_val:
                trade_score = max(0, trade_score - 30)
                trade_reasons.append(f"תקציב {val} מתחת למינימום המבוקש {min_val}")
            elif max_val is not None and val > max_val:
                trade_score = max(0, trade_score - 30)
                trade_reasons.append(f"תקציב {val} מעל המקסימום המבוקש {max_val}")
            else:
                trade_reasons.append(f"תקציב {val} ₪ בטווח המבוקש")
        except (ValueError, TypeError):
            pass

    business_fit = min(100, trade_score + location_score)
    reasons["business_fit"] = trade_reasons

    # -------------------------------------------------------------------------
    # 2. דחיפות וטריות (urgency) — 0 עד 100
    # -------------------------------------------------------------------------
    urgency_score = 50  # ברירת מחדל
    urgency_reasons = []

    now = datetime.now(timezone.utc)

    # טריות פרסום
    if published_at:
        hours_old = (now - published_at).total_seconds() / 3600.0
        if hours_old <= 12:
            urgency_score = 90
            urgency_reasons.append(f"טרי מאוד (פורסם לפני {int(hours_old)} שעות)")
        elif hours_old <= 48:
            urgency_score = 75
            urgency_reasons.append(f"פורסם ביומיים האחרונים ({int(hours_old)} שעות)")
        elif hours_old <= 168:
            urgency_score = 55
            urgency_reasons.append("פורסם בשבוע האחרון")
        else:
            urgency_score = 30
            urgency_reasons.append("פורסם לפני יותר משבוע")
    else:
        urgency_reasons.append("מועד פרסום מקורי לא צוין")

    # קירבה למועד סיום/דדליין
    deadline_val = extracted.deadline.value
    if deadline_val:
        urgency_reasons.append(f"קיים מועד אחרון מוגדר: {deadline_val}")
        # אם יש דדליין, הדחיפות עולה
        urgency_score = min(100, urgency_score + 15)

    urgency = min(100, max(0, urgency_score))
    reasons["urgency"] = urgency_reasons

    # -------------------------------------------------------------------------
    # 3. ביטחון בחילוץ (confidence) — 0 עד 100
    # -------------------------------------------------------------------------
    # ממוצע ציוני הביטחון של השדות המרכזיים
    c_title = extracted.title.confidence or 0.5
    c_loc = extracted.location.confidence or 0.5
    c_work = extracted.work_type.confidence or 0.5

    avg_conf = (c_title + c_loc + c_work) / 3.0
    confidence = int(round(avg_conf * 100))
    reasons["confidence"] = [
        f"כותרת: {int(c_title*100)}%, מיקום: {int(c_loc*100)}%, עבודה: {int(c_work*100)}%"
    ]

    # -------------------------------------------------------------------------
    # זיהוי מסלול מהיר (Fast-Track)
    # -------------------------------------------------------------------------
    bf_thresh = fast_track_config.get("business_fit_threshold", 80)
    urg_thresh = fast_track_config.get("urgency_threshold", 70)
    conf_thresh = fast_track_config.get("confidence_threshold", 0.7)

    is_fast_track = (
        business_fit >= bf_thresh
        and urgency >= urg_thresh
        and (confidence / 100.0) >= conf_thresh
    )

    return OpportunityScore(
        business_fit=business_fit,
        urgency=urgency,
        confidence=confidence,
        is_fast_track=is_fast_track,
        score_reasons=reasons,
    )
