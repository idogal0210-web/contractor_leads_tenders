"""
בדיקות יחידה למנוע השיגור המבוסס-כללים (Rule-Based Dispatcher).
"""
from notifications.dispatcher import decide_dispatch, DispatchDecision


def test_dispatcher_already_notified_skips():
    """התראה שכבר נשלחה לא תישלח שוב לעולם (מניעת ספאם)."""
    res = decide_dispatch(
        opportunity_id="123",
        match_status="fit",
        category="service_request",
        is_fast_track=True,
        score_business_fit=95,
        score_urgency=90,
        score_confidence=90,
        already_notified=True,
        fast_track_config={},
    )
    assert res.decision == DispatchDecision.SKIP


def test_dispatcher_irrelevant_skips():
    """פריט שסווג כלא רלוונטי אינו נשלח."""
    res = decide_dispatch(
        opportunity_id="123",
        match_status="fit",
        category="irrelevant",
        is_fast_track=False,
        score_business_fit=90,
        score_urgency=50,
        score_confidence=90,
        already_notified=False,
        fast_track_config={},
    )
    assert res.decision == DispatchDecision.SKIP


def test_dispatcher_fast_track_sends_now():
    """מסלול מהיר משגר התראה מידית (SEND_NOW) ועוקף חלונות תזמון."""
    res = decide_dispatch(
        opportunity_id="123",
        match_status="fit",
        category="service_request",
        is_fast_track=True,
        score_business_fit=85,
        score_urgency=80,
        score_confidence=85,
        already_notified=False,
        fast_track_config={},
    )
    assert res.decision == DispatchDecision.SEND_NOW
    assert "email" in res.channels
    assert "telegram" in res.channels


def test_dispatcher_fit_sends_queued():
    """התאמה רגילה נשלחת בתור (SEND_QUEUED) לחלון ההפצה הבא."""
    res = decide_dispatch(
        opportunity_id="123",
        match_status="fit",
        category="service_request",
        is_fast_track=False,
        score_business_fit=70,
        score_urgency=50,
        score_confidence=75,
        already_notified=False,
        fast_track_config={},
    )
    assert res.decision == DispatchDecision.SEND_QUEUED
