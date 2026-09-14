"""
בדיקות יחידה לסיווג מתקדם (6 קטגוריות).
"""
# import pytest
from core.db.enums import OpportunityCategory
from processors.classifier import classify_opportunity
from processors.llm_extractor import ExtractedOpportunity, ExtractedField


def create_mock_extracted(title="", work_type="", is_tender=False, tender_num=None):
    return ExtractedOpportunity(
        title=ExtractedField(value=title, confidence=0.9),
        location=ExtractedField(value="תל אביב", confidence=0.9),
        budget=ExtractedField(value=None, confidence=0.0),
        work_type=ExtractedField(value=work_type, confidence=0.9),
        deadline=ExtractedField(value=None, confidence=0.0),
        contact=ExtractedField(value="050-1234567", confidence=0.9),
        tender_number=tender_num,
        opportunity_type="tender" if is_tender else "lead",
        summary="סיכום בדיקה",
    )


def test_classify_official_tender():
    """מכרז רשמי מסווג כ-service_request עם ביטחון גבוה."""
    opp = create_mock_extracted(title="מכרז פומבי 12/2026", is_tender=True, tender_num="12/2026")
    cat, conf = classify_opportunity(opp, "מכרז פומבי לביצוע עבודות עפר")
    assert cat == OpportunityCategory.SERVICE_REQUEST
    assert conf >= 0.95


def test_classify_subcontracting():
    """חיפוש קבלן משנה מסווג כ-subcontracting."""
    opp = create_mock_extracted(title="דרוש קבלן משנה לעבודות שלד", work_type="שלד")
    cat, conf = classify_opportunity(opp, "אנחנו קבלן ראשי ומחפשים קבלן משנה לביצוע פרויקט")
    assert cat == OpportunityCategory.SUBCONTRACTING


def test_classify_recommendation_request():
    """בקשת המלצה בקבוצה מסווגת כ-recommendation_request."""
    opp = create_mock_extracted(title="מחפש המלצה על אינסטלטור", work_type="אינסטלציה")
    cat, conf = classify_opportunity(opp, "היי חברים, מישהו מכיר אינסטלטור טוב ואמין באזור המרכז?")
    assert cat == OpportunityCategory.RECOMMENDATION_REQUEST


def test_classify_provider_ad():
    """פרסומת ספק/קבלן מסווגת כ-provider_ad ולא כליד אמיתי."""
    opp = create_mock_extracted(title="שירותי שיפוץ מקצועיים", work_type="שיפוץ כללי")
    cat, conf = classify_opportunity(opp, "חברתנו מתמחה בכל סוגי השיפוצים, אנו מציעים מחירים ללא תחרות, התקשרו עכשיו")
    assert cat == OpportunityCategory.PROVIDER_AD


def test_classify_service_request():
    """פנייה מפורשת של לקוח לקבלת עבודה מסווגת כ-service_request."""
    opp = create_mock_extracted(title="דרוש קבלן לשיפוץ דירה", work_type="שיפוץ")
    cat, conf = classify_opportunity(opp, "שלום, מחפש קבלן מוסמך לעבודות ריצוף ואיטום בדירת 4 חדרים")
    assert cat == OpportunityCategory.SERVICE_REQUEST
