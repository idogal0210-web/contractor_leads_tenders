"""
בדיקות יחידה למנוע ההתאמה מול פרופיל הקבלן (Matcher).
"""
from core.db.enums import MatchStatus
from processors.matcher import match_to_profile
from processors.scorer import OpportunityScore
from processors.llm_extractor import ExtractedOpportunity, ExtractedField


def mock_profile():
    return {
        "service_area": "ארצי",
        "excluded_trades": ["אסבסט", "פירוק אסבסט"],
        "min_project_value": 5000,
        "max_project_value": 1000000,
    }


def test_matcher_excluded_trade():
    """עבודה המכילה מקצוע שהוחרג מפורשות מקבלת NO_FIT מיידי."""
    opp = ExtractedOpportunity(
        title=ExtractedField(value="פירוק גג אסבסט", confidence=0.95),
        location=ExtractedField(value="פתח תקווה", confidence=0.9),
        budget=ExtractedField(value=30000, confidence=0.9),
        work_type=ExtractedField(value="פירוק אסבסט", confidence=0.95),
        deadline=ExtractedField(value=None, confidence=0.0),
        contact=ExtractedField(value="050-0000000", confidence=0.9),
        opportunity_type="lead",
        summary="אסבסט",
    )
    score = OpportunityScore(business_fit=80, urgency=50, confidence=90, is_fast_track=False, score_reasons={})
    res = match_to_profile(opp, mock_profile(), score)

    assert res.status == MatchStatus.NO_FIT
    assert "הוחרג מפורשות" in res.reason


def test_matcher_fit_high_score():
    """התאמה עסקית טובה ללא בעיות מקבלת FIT."""
    opp = ExtractedOpportunity(
        title=ExtractedField(value="שיפוץ כללי בדירה", confidence=0.9),
        location=ExtractedField(value="חולון", confidence=0.9),
        budget=ExtractedField(value=150000, confidence=0.9),
        work_type=ExtractedField(value="שיפוץ ובנייה", confidence=0.9),
        deadline=ExtractedField(value=None, confidence=0.0),
        contact=ExtractedField(value="050-0000000", confidence=0.9),
        opportunity_type="lead",
        summary="שיפוץ",
    )
    score = OpportunityScore(business_fit=85, urgency=60, confidence=90, is_fast_track=False, score_reasons={})
    res = match_to_profile(opp, mock_profile(), score)

    assert res.status == MatchStatus.FIT


def test_matcher_needs_review_low_confidence():
    """רמת ביטחון נמוכה מועברת לבדיקה אנושית (NEEDS_REVIEW)."""
    opp = ExtractedOpportunity(
        title=ExtractedField(value="פרויקט לא ברור", confidence=0.3),
        location=ExtractedField(value=None, confidence=0.2),
        budget=ExtractedField(value=None, confidence=0.0),
        work_type=ExtractedField(value="עבודות שונות", confidence=0.3),
        deadline=ExtractedField(value=None, confidence=0.0),
        contact=ExtractedField(value=None, confidence=0.0),
        opportunity_type="lead",
        summary="לא ברור",
    )
    score = OpportunityScore(business_fit=50, urgency=40, confidence=30, is_fast_track=False, score_reasons={})
    res = match_to_profile(opp, mock_profile(), score)

    assert res.status == MatchStatus.NEEDS_REVIEW
    assert len(res.missing_info) > 0
