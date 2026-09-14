"""
בדיקות יחידה לניקוד רב-ממדי (3 מדדים נפרדים) ו-Fast-Track.
"""
from datetime import datetime, timezone, timedelta
from processors.scorer import score_opportunity
from processors.llm_extractor import ExtractedOpportunity, ExtractedField


def mock_profile():
    return {
        "service_area": "ארצי",
        "trade_keywords_hebrew": {
            "electrical": ["חשמל", "חשמלאי", "גנרטור"],
            "plumbing": ["אינסטלציה", "שרברב", "צנרת"],
        },
        "min_project_value": 10000,
        "max_project_value": 5000000,
    }


def mock_fast_track_config():
    return {
        "business_fit_threshold": 80,
        "urgency_threshold": 70,
        "confidence_threshold": 0.7,
    }


def test_scorer_full_match_and_fast_track():
    """התאמה מלאה למקצוע + טרי מאוד -> זכאות ל-Fast-Track."""
    opp = ExtractedOpportunity(
        title=ExtractedField(value="דרוש חשמלאי מוסמך להחלפת לוח חשמל", confidence=0.95),
        location=ExtractedField(value="תל אביב", confidence=0.9),
        budget=ExtractedField(value=25000, confidence=0.85),
        work_type=ExtractedField(value="עבודות חשמל", confidence=0.95),
        deadline=ExtractedField(value="2026-09-20", confidence=0.8),
        contact=ExtractedField(value="052-1111111", confidence=0.9),
        opportunity_type="lead",
        summary="החלפת לוח ראשי",
    )

    now = datetime.now(timezone.utc) - timedelta(hours=2)
    score = score_opportunity(
        extracted=opp,
        contractor_profile=mock_profile(),
        fast_track_config=mock_fast_track_config(),
        published_at=now,
    )

    assert score.business_fit == 100  # 60 (חשמל) + 40 (ארצי)
    assert score.urgency >= 75
    assert score.confidence >= 80
    assert score.is_fast_track is True


def test_scorer_no_trade_match():
    """ללא התאמה למקצוע -> ציון נמוך וללא Fast-Track."""
    opp = ExtractedOpportunity(
        title=ExtractedField(value="מכירת ציוד משרדי משומש", confidence=0.8),
        location=ExtractedField(value="חיפה", confidence=0.8),
        budget=ExtractedField(value=None, confidence=0.0),
        work_type=ExtractedField(value="ציוד משרדי", confidence=0.8),
        deadline=ExtractedField(value=None, confidence=0.0),
        contact=ExtractedField(value="contact@test.com", confidence=0.8),
        opportunity_type="lead",
        summary="מכירת ריהוט",
    )

    score = score_opportunity(
        extracted=opp,
        contractor_profile=mock_profile(),
        fast_track_config=mock_fast_track_config(),
    )

    assert score.business_fit <= 50
    assert score.is_fast_track is False
