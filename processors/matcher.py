"""
processors/matcher.py — מנוע התאמה לפרופיל הקבלן (Contractor Profile Matching).

מחזיר אחד מ-3 מצבים בלבד:
1. FIT — מתאים לפי הנתונים.
2. NO_FIT — לא מתאים (בצירוף סיבה מדויקת).
3. NEEDS_REVIEW — דורש בדיקה אנושית (בצירוף המידע החסר או סתירה שהתגלתה).

הכרעה על סתירות או אי-ודאות מועברת תמיד לבדיקה אנושית ולא נסגרת שרירותית ע"י ה-LLM.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING
from core.db.enums import MatchStatus

if TYPE_CHECKING:
    from processors.llm_extractor import ExtractedOpportunity
    from processors.scorer import OpportunityScore


@dataclass
class MatchResult:
    """תוצאת השוואה והתאמה לפרופיל הקבלן."""
    status: MatchStatus
    reason: str
    missing_info: list[str] = field(default_factory=list)


def match_to_profile(
    extracted: ExtractedOpportunity,
    contractor_profile: dict[str, Any],
    score: OpportunityScore,
) -> MatchResult:
    """
    השוואת השדות שחולצו לפרופיל הקבלן היעד.
    """
    missing: list[str] = []

    # 1. בדיקת החרגות מפורשות (Excluded Trades)
    excluded_trades = contractor_profile.get("excluded_trades", [])
    work_val = (extracted.work_type.value or "").lower()
    title_val = (extracted.title.value or "").lower()
    combined_val = f"{work_val} {title_val}"

    for exc in excluded_trades:
        if exc.lower() in combined_val:
            return MatchResult(
                status=MatchStatus.NO_FIT,
                reason=f"העבודה כוללת מקצוע שהוחרג מפורשות בפרופיל: {exc}",
            )

    # 2. בדיקת ביטחון החילוץ — אם רמת הביטחון נמוכה מאוד, נדרשת בדיקה אנושית
    if score.confidence < 45:
        missing.append("טקסט המקור אינו חד-משמעי או שחילוץ המידע בעל רמת ודאות נמוכה")

    # 3. בדיקת סוג עבודה/מקצוע
    if not extracted.work_type.value:
        missing.append("סוג העבודה/המקצוע אינו מוגדר בבירור")

    # 4. בדיקת מגבלות תקציב מוחלטות (אם קיימות)
    budget_val = extracted.budget.value
    if budget_val is not None:
        try:
            val = float(budget_val)
            min_val = contractor_profile.get("min_project_value")
            max_val = contractor_profile.get("max_project_value")

            if min_val is not None and val < min_val:
                return MatchResult(
                    status=MatchStatus.NO_FIT,
                    reason=f"תקציב הפרויקט ({val:,.0f} ₪) נמוך מסף המינימום המוגדר ({min_val:,.0f} ₪)",
                )
            if max_val is not None and val > max_val:
                return MatchResult(
                    status=MatchStatus.NO_FIT,
                    reason=f"תקציב הפרויקט ({val:,.0f} ₪) עולה על תקרת המקסימום המוגדרת ({max_val:,.0f} ₪)",
                )
        except (ValueError, TypeError):
            pass

    # 5. בדיקת התאמה עסקית
    if score.business_fit >= 60 and not missing:
        return MatchResult(
            status=MatchStatus.FIT,
            reason=f"התאמה גבוהה למקצועות הקבלן (ציון התאמה: {score.business_fit}/100)",
        )

    if score.business_fit < 35 and not missing:
        return MatchResult(
            status=MatchStatus.NO_FIT,
            reason=f"אין התאמה למקצועות הקבלן (ציון התאמה: {score.business_fit}/100)",
        )

    # 6. בכל מקרה אחר של ספק, סתירה או מידע חלקי — מעבר לבדיקה אנושית
    if not missing:
        missing.append("ציון התאמה בינוני — נדרשת הכרעת קבלן לגבי כדאיות הפרויקט")

    return MatchResult(
        status=MatchStatus.NEEDS_REVIEW,
        reason="נדרשת בדיקה אנושית של פרטי ההזדמנות",
        missing_info=missing,
    )
