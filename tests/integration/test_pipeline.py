"""
בדיקת אינטגרציה מלאה (E2E Pipeline) על דוגמת ליד.
"""
# import pytest
from unittest.mock import patch, AsyncMock
from processors.deduplication import compute_content_hash
from processors.classifier import classify_opportunity
from processors.scorer import score_opportunity
from processors.matcher import match_to_profile, MatchStatus
from notifications.dispatcher import decide_dispatch, DispatchDecision
from processors.llm_extractor import ExtractedOpportunity, ExtractedField


def test_full_pipeline_flow():
    # 1. טקסט גולמי שהתקבל מוואטסאפ או סקרייפר
    raw_lead = "מחפש קבלן מוסמך דחוף לעבודות שיפוץ, טיח וצבע במרכז תל אביב. תקציב משוער 45,000 שח. טלפון: 054-9999999"

    # 2. שלב מניעת כפילויות
    content_hash = compute_content_hash(raw_lead)
    assert len(content_hash) == 64

    # 3. שלב חילוץ מובנה (mock של תוצאת Gemini 3.8 Flash)
    extracted = ExtractedOpportunity(
        title=ExtractedField(value="עבודות שיפוץ, טיח וצבע", evidence_text="שיפוץ, טיח וצבע", confidence=0.95),
        location=ExtractedField(value="תל אביב", evidence_text="במרכז תל אביב", confidence=0.95),
        budget=ExtractedField(value=45000, evidence_text="תקציב משוער 45,000 שח", confidence=0.9),
        work_type=ExtractedField(value="שיפוץ, צבע וטיח", evidence_text="עבודות שיפוץ, טיח וצבע", confidence=0.95),
        deadline=ExtractedField(value=None, evidence_text=None, confidence=0.0),
        contact=ExtractedField(value="054-9999999", evidence_text="טלפון: 054-9999999", confidence=0.95),
        opportunity_type="lead",
        summary="בקשת שיפוץ וצבע בתל אביב",
    )

    # 4. סיווג
    category, cat_conf = classify_opportunity(extracted, raw_lead)
    assert category.value in ["service_request", "subcontracting"]

    # 5. ניקוד (פרופיל קבלן MVP)
    contractor_profile = {
        "service_area": "ארצי",
        "trade_keywords_hebrew": {
            "painting": ["צבע", "טיח"],
            "general_contractor": ["שיפוץ"],
        },
        "excluded_trades": [],
        "min_project_value": None,
        "max_project_value": None,
    }
    fast_track_config = {
        "business_fit_threshold": 80,
        "urgency_threshold": 70,
        "confidence_threshold": 0.7,
    }

    score = score_opportunity(extracted, contractor_profile, fast_track_config)
    assert score.business_fit >= 70

    # 6. התאמה לפרופיל
    match_res = match_to_profile(extracted, contractor_profile, score)
    assert match_res.status == MatchStatus.FIT

    # 7. החלטת שיגור התראה (Rule-based)
    dispatch_res = decide_dispatch(
        opportunity_id="test-123",
        match_status=match_res.status.value,
        category=category.value,
        is_fast_track=score.is_fast_track,
        score_business_fit=score.business_fit,
        score_urgency=score.urgency,
        score_confidence=score.confidence,
        already_notified=False,
        fast_track_config=fast_track_config,
    )

    assert dispatch_res.decision in [DispatchDecision.SEND_NOW, DispatchDecision.SEND_QUEUED]
    assert "email" in dispatch_res.channels
    assert "telegram" in dispatch_res.channels
