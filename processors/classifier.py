"""
processors/classifier.py — סיווג מתקדם (לא בינארי) ל-6 קטגוריות.

מסווג כל פריט על פי חוקים מוגדרים:
1. service_request — בקשת שירות (מחפש קבלן/איש מקצוע לבצע עבודה)
2. provider_ad — פרסומת של ספק או קבלן המציע שירותים
3. recommendation_request — בקשת המלצה על בעל מקצוע
4. subcontracting — קבלן ראשי המחפש קבלן משנה לעבודה
5. irrelevant — לא רלוונטי לתחומי הבנייה/שיפוצים/עבודות
6. uncertain — לא ודאי, דורש בחינה
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING
from core.db.enums import OpportunityCategory

if TYPE_CHECKING:
    from processors.llm_extractor import ExtractedOpportunity

# מילות מפתח בעברית לכל קטגוריה
KEYWORDS = {
    OpportunityCategory.SUBCONTRACTING: [
        "קבלן משנה", "קבלני משנה", "דרוש צוות", "דרושים עובדים", "פועלים לפרויקט",
        "עבודת קבלנות משנה", "קבלן לביצוע שלד", "מחפש צוות חשמל", "צוות גבס"
    ],
    OpportunityCategory.RECOMMENDATION_REQUEST: [
        "המלצה", "מחפש המלצה", "מישהו מכיר", "מי מכיר", "מחפשת המלצה",
        "יש לכם מישהו", "המלצות על", "מחפשים המלצה", "מכירים קבלן"
    ],
    OpportunityCategory.PROVIDER_AD: [
        "אנו מציעים", "שירותי שיפוץ מקצועיים", "הנחה מיוחדת", "מבצע", "התקשרו עכשיו",
        "חברתנו מתמחה", "ניסיון של שנים", "במחירים ללא תחרות", "שירותי קבלנות",
        "ייעוץ חינם", "מזמינים אתכם ליצור קשר"
    ],
    OpportunityCategory.SERVICE_REQUEST: [
        "מחפש קבלן", "דרוש קבלן", "דרושה עבודה", "מחפש איש מקצוע", "צריך שיפוץ",
        "עבודות חשמל", "תיקון אינסטלציה", "מחפש הצעת מחיר", "דרוש שיפוץ", "מכרז",
        "עבודות צבע", "בניית קיר", "איטום גג", "ריצוף דירה", "החלפת צנרת"
    ],
}


def classify_opportunity(
    extracted: ExtractedOpportunity,
    raw_text: str,
    is_tender: bool = False,
) -> tuple[OpportunityCategory, float]:
    """
    סיווג הזדמנות על בסיס הנתונים שחולצו וטקסט המקור.
    מחזיר זוג: (קטגוריה, רמת ביטחון).
    """
    # 1. אם זה מכרז רשמי או שיש מספר מכרז מפורש -> תמיד בקשת שירות ציבורית
    if is_tender or extracted.tender_number or extracted.opportunity_type == "tender":
        return OpportunityCategory.SERVICE_REQUEST, 0.98

    text_lower = raw_text.lower()
    title_text = (extracted.title.value or "").lower()
    work_text = (extracted.work_type.value or "").lower()
    combined_search_text = f"{title_text} {work_text} {text_lower}"

    # 2. בדיקת קבלנות משנה
    for kw in KEYWORDS[OpportunityCategory.SUBCONTRACTING]:
        if kw in combined_search_text:
            return OpportunityCategory.SUBCONTRACTING, 0.90

    # 3. בדיקת בקשת המלצה
    for kw in KEYWORDS[OpportunityCategory.RECOMMENDATION_REQUEST]:
        if kw in combined_search_text:
            return OpportunityCategory.RECOMMENDATION_REQUEST, 0.85

    # 4. בדיקת פרסומת ספק (מודעה ולא ביקוש אמיתי)
    for kw in KEYWORDS[OpportunityCategory.PROVIDER_AD]:
        if kw in combined_search_text:
            return OpportunityCategory.PROVIDER_AD, 0.88

    # 5. בדיקת בקשת שירות ישירה
    for kw in KEYWORDS[OpportunityCategory.SERVICE_REQUEST]:
        if kw in combined_search_text:
            return OpportunityCategory.SERVICE_REQUEST, 0.85

    # 6. בדיקת רלוונטיות כללית
    construction_general_terms = [
        "שיפוץ", "בנייה", "חשמל", "אינסטלציה", "צבע", "גבס", "עפר", "מיזוג",
        "איטום", "ריצוף", "הריסה", "פיתוח", "קבלן", "תשתיות"
    ]
    has_relevant_term = any(term in combined_search_text for term in construction_general_terms)

    if not has_relevant_term and len(raw_text) > 100:
        return OpportunityCategory.IRRELEVANT, 0.80

    if has_relevant_term:
        # נמצא מונח רלוונטי אך לא נוסח פנייה מובהק
        return OpportunityCategory.SERVICE_REQUEST, 0.65

    return OpportunityCategory.UNCERTAIN, 0.50
