"""
notifications/dispatcher.py — מנוע שיגור התראות מבוסס-כללים.

ה-LLM לעולם לא מחליט אם לשלוח. רק הכללים המפורשים בקובץ זה קובעים.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

import structlog

from config.settings import settings

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from core.db.models import Opportunity

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants — חלונות שיגור (שעון ישראל UTC+3)
# ---------------------------------------------------------------------------

# חלונות שיגור: 08:00–09:00 ו-18:00–19:00 שעון ישראל
DISPATCH_WINDOWS_ISRAEL: list[tuple[int, int]] = [
    (8, 9),   # בוקר
    (18, 19), # ערב
]

# היסט UTC לשעון ישראל (IST = UTC+3, ללא DST)
ISRAEL_UTC_OFFSET_HOURS = 3


# ---------------------------------------------------------------------------
# Enums & Dataclasses
# ---------------------------------------------------------------------------

class DispatchDecision(str, Enum):
    """החלטת שיגור — ערך enum כמחרוזת לשמירה ב-DB."""
    SEND_NOW = "send_now"        # מסלול מהיר: עוקף חלונות זמן
    SEND_QUEUED = "send_queued"  # ממתין לחלון שיגור הבא (בוקר/ערב)
    SKIP = "skip"                # לא לשלוח (לא רלוונטי, כפול, no_fit)


@dataclass
class DispatchResult:
    """תוצאת החלטת השיגור."""
    decision: DispatchDecision
    reason: str
    channels: list[str] = field(default_factory=lambda: ["email", "telegram"])


# ---------------------------------------------------------------------------
# Core Rule Engine
# ---------------------------------------------------------------------------

def decide_dispatch(
    opportunity_id: str,
    match_status: str,          # 'fit' | 'no_fit' | 'needs_review'
    category: str,
    is_fast_track: bool,
    score_business_fit: int,
    score_urgency: int,
    score_confidence: int,
    already_notified: bool,
    fast_track_config: dict,
) -> DispatchResult:
    """
    מנוע החלטות שיגור מבוסס-כללים טהור. אין מעורבות LLM.

    כללים לפי סדר עדיפות:
    1. אם already_notified → SKIP (אין כפילויות)
    2. אם category == 'irrelevant' → SKIP
    3. אם match_status == 'no_fit' → SKIP
    4. אם is_fast_track == True → SEND_NOW (עוקף חלונות זמן)
    5. אם match_status == 'fit' AND score_business_fit >= 60 → SEND_QUEUED
    6. אם match_status == 'needs_review' AND score_business_fit >= 50 → SEND_QUEUED
    7. אחרת → SKIP

    ערוצים: תמיד אימייל + טלגרם ב-MVP.

    Args:
        opportunity_id: מזהה ייחודי של ההזדמנות (לצורך לוגינג בלבד).
        match_status: תוצאת התאמה — 'fit', 'no_fit', 'needs_review'.
        category: קטגוריית ההזדמנות.
        is_fast_track: האם ההזדמנות מסומנת כמסלול מהיר.
        score_business_fit: ציון התאמה עסקית (0–100).
        score_urgency: ציון דחיפות (0–100).
        score_confidence: ציון ביטחון (0–100).
        already_notified: האם כבר נשלחה התראה על הזדמנות זו.
        fast_track_config: מילון עם ספי fast-track מה-settings.

    Returns:
        DispatchResult עם ההחלטה, הסיבה, והערוצים.
    """
    log_ctx = log.bind(opportunity_id=opportunity_id, category=category, match_status=match_status)

    # כלל 1: ללא כפילויות
    if already_notified:
        log_ctx.debug("dispatch_skip_duplicate")
        return DispatchResult(
            decision=DispatchDecision.SKIP,
            reason="already_notified — כבר נשלחה התראה על הזדמנות זו",
            channels=[],
        )

    # כלל 2: לא רלוונטי
    if category == "irrelevant":
        log_ctx.debug("dispatch_skip_irrelevant")
        return DispatchResult(
            decision=DispatchDecision.SKIP,
            reason="category=irrelevant — פרסום לא רלוונטי",
            channels=[],
        )

    # כלל 3: לא מתאים
    if match_status == "no_fit":
        log_ctx.debug("dispatch_skip_no_fit")
        return DispatchResult(
            decision=DispatchDecision.SKIP,
            reason="match_status=no_fit — ההזדמנות לא מתאימה לפרופיל",
            channels=[],
        )

    # כלל 4: מסלול מהיר — שיגור מיידי
    if is_fast_track:
        log_ctx.info(
            "dispatch_send_now_fast_track",
            score_business_fit=score_business_fit,
            score_urgency=score_urgency,
        )
        return DispatchResult(
            decision=DispatchDecision.SEND_NOW,
            reason="fast_track=True — מסלול מהיר, שיגור מיידי",
            channels=["email", "telegram"],
        )

    # כלל 5: התאמה מלאה עם ציון מינימלי
    if match_status == "fit" and score_business_fit >= 60:
        log_ctx.info("dispatch_send_queued_fit", score_business_fit=score_business_fit)
        return DispatchResult(
            decision=DispatchDecision.SEND_QUEUED,
            reason=f"fit + score_business_fit={score_business_fit} >= 60 — ממתין לחלון שיגור",
            channels=["email", "telegram"],
        )

    # כלל 6: זקוק לסקירה עם ציון מינימלי
    if match_status == "needs_review" and score_business_fit >= 50:
        log_ctx.info("dispatch_send_queued_needs_review", score_business_fit=score_business_fit)
        return DispatchResult(
            decision=DispatchDecision.SEND_QUEUED,
            reason=f"needs_review + score_business_fit={score_business_fit} >= 50 — ממתין לחלון שיגור",
            channels=["email", "telegram"],
        )

    # כלל 7: ברירת מחדל — דלג
    log_ctx.debug(
        "dispatch_skip_default",
        score_business_fit=score_business_fit,
        match_status=match_status,
    )
    return DispatchResult(
        decision=DispatchDecision.SKIP,
        reason=f"ציון נמוך מדי או סטטוס לא ממופה: match_status={match_status}, score_business_fit={score_business_fit}",
        channels=[],
    )


def is_in_dispatch_window(now: datetime | None = None) -> bool:
    """
    בדיקת האם השעה הנוכחית בתוך חלון שיגור מוגדר.

    חלונות שיגור: 08:00–09:00 ו-18:00–19:00 שעון ישראל (UTC+3).
    מסלול מהיר עוקף בדיקה זו לחלוטין.

    Args:
        now: datetime לבדיקה. ברירת מחדל: datetime.now(UTC).

    Returns:
        True אם השעה בתוך חלון שיגור, False אחרת.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # המרה לשעון ישראל
    israel_hour = (now.hour + ISRAEL_UTC_OFFSET_HOURS) % 24

    for window_start, window_end in DISPATCH_WINDOWS_ISRAEL:
        if window_start <= israel_hour < window_end:
            log.debug(
                "dispatch_window_active",
                israel_hour=israel_hour,
                window=f"{window_start:02d}:00-{window_end:02d}:00",
            )
            return True

    return False


async def execute_dispatch(
    opportunity: "Opportunity",
    decision: DispatchResult,
    db: "Session",
) -> None:
    """
    מבצע את השיגור: שולח התראות ושומר ב-notifications table.

    רשומת ה-Notification נשמרת לפני השליחה (atomic log לאודיט).
    בסיום עדכון הסטטוס ל-'sent' או 'failed'.

    Args:
        opportunity: אובייקט ה-Opportunity מה-ORM.
        decision: תוצאת DispatchResult מה-rule engine.
        db: Session פעיל של SQLAlchemy.
    """
    from datetime import datetime, timezone
    from core.db.models import Notification, NotificationChannel
    from notifications.email_sender import send_opportunity_alert
    from notifications.telegram_sender import send_opportunity_alert_telegram

    if decision.decision == DispatchDecision.SKIP:
        log.debug("execute_dispatch_skipped", opportunity_id=str(opportunity.id))
        return

    # בניית snapshot של נתוני ההזדמנות לאודיט
    opportunity_snapshot = {
        "id": str(opportunity.id),
        "title": opportunity.title_value,
        "category": opportunity.category,
        "match_status": opportunity.match_status,
        "score_business_fit": opportunity.score_business_fit,
        "score_urgency": opportunity.score_urgency,
        "score_confidence": opportunity.score_confidence,
        "is_fast_track": opportunity.is_fast_track,
        "location": opportunity.location_value,
        "budget_value": opportunity.budget_value,
        "budget_currency": opportunity.budget_currency,
        "work_type": opportunity.work_type_value,
        "deadline": opportunity.deadline_value.isoformat() if opportunity.deadline_value else None,
        "tender_number": opportunity.tender_number,
        "publisher_name": opportunity.publisher_name,
        "opportunity_type": opportunity.opportunity_type,
        "snapshot_ts": datetime.now(timezone.utc).isoformat(),
    }

    # בניית מילון נתוני ההזדמנות לתבניות
    opportunity_data = {
        **opportunity_snapshot,
        "source_url": opportunity.source_item.url if opportunity.source_item else None,
        "tender_events": [
            {
                "event_type": e.event_type,
                "event_date": e.event_date.isoformat() if e.event_date else None,
                "notes": e.notes,
            }
            for e in (opportunity.tender_events or [])
        ],
    }

    # יצירת רשומות Notification לפני השליחה (write-ahead log לאודיט)
    notification_records: list[Notification] = []
    for channel_str in decision.channels:
        channel = NotificationChannel(channel_str)
        recipient = (
            settings.smtp_from
            if channel == NotificationChannel.EMAIL
            else settings.telegram_chat_id
        )
        subject = (
            f"{'🔴 FAST-TRACK' if opportunity.is_fast_track else '🟡 הזדמנות חדשה'}: "
            f"{opportunity.title_value or 'ללא כותרת'}"
        )
        notif = Notification(
            id=uuid.uuid4(),
            opportunity_id=opportunity.id,
            channel=channel,
            recipient=recipient,
            subject=subject if channel == NotificationChannel.EMAIL else None,
            body_preview=(opportunity.match_reason or "")[:500],
            status="pending",
            opportunity_version_snapshot=opportunity_snapshot,
        )
        db.add(notif)
        notification_records.append(notif)

    # שמירת רשומות ה-pending לפני השליחה
    db.flush()
    log.info(
        "notifications_pre_send_flushed",
        opportunity_id=str(opportunity.id),
        count=len(notification_records),
    )

    # שיגור בפועל לכל ערוץ
    for notif in notification_records:
        success = False
        error_detail: str | None = None

        try:
            if notif.channel == NotificationChannel.EMAIL:
                success = await send_opportunity_alert(
                    opportunity_data=opportunity_data,
                    recipient_email=notif.recipient,
                    is_fast_track=opportunity.is_fast_track,
                )
            elif notif.channel == NotificationChannel.TELEGRAM:
                success = await send_opportunity_alert_telegram(
                    opportunity_data=opportunity_data,
                    is_fast_track=opportunity.is_fast_track,
                )
        except Exception as exc:
            error_detail = str(exc)
            log.error(
                "notification_send_error",
                channel=notif.channel,
                opportunity_id=str(opportunity.id),
                error=error_detail,
                exc_info=True,
            )

        # עדכון סטטוס הרשומה
        notif.status = "sent" if success else "failed"
        notif.sent_at = datetime.now(timezone.utc) if success else None
        notif.error_detail = error_detail

        log.info(
            "notification_result",
            channel=notif.channel,
            opportunity_id=str(opportunity.id),
            success=success,
        )

    # commit הסופי
    db.commit()
    log.info(
        "execute_dispatch_complete",
        opportunity_id=str(opportunity.id),
        decision=decision.decision,
        channels=decision.channels,
    )
