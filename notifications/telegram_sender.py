"""
notifications/telegram_sender.py — שליחת התראות ודוחות לטלגרם באמצעות Telegram Bot API.

תומך בפורמט HTML, זיהוי Fast-Track והתאמת טקסט RTL.
"""
from __future__ import annotations

import html
from typing import Any
import httpx
import structlog
from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential

from config.settings import settings

log = structlog.get_logger(__name__)


async def send_telegram_message(
    chat_id: str,
    text: str,
    parse_mode: str = "HTML",
) -> bool:
    """שליחת הודעת טקסט ל-Telegram Bot API."""
    token = settings.telegram_bot_token
    if not token or token.startswith("your_") or not chat_id or chat_id.startswith("your_"):
        log.warning("telegram_credentials_missing_skipping_send")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False,
    }

    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=1, min=2, max=6),
            reraise=True,
        ):
            with attempt:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        log.info("telegram_message_sent", chat_id=chat_id)
                        return True
                    else:
                        log.error("telegram_send_status_error", status=resp.status_code, body=resp.text)
                        return False
    except Exception as exc:
        log.error("telegram_send_failed", error=str(exc))
        return False


async def send_opportunity_alert_telegram(
    opportunity_data: dict[str, Any],
    is_fast_track: bool = False,
) -> bool:
    """פורמוט ושליחה של התראת הזדמנות לטלגרם."""
    chat_id = settings.telegram_chat_id
    if not chat_id:
        return False

    is_tender = opportunity_data.get("opportunity_type") == "tender"
    badge = "🔴 <b>[מסלול מהיר - FAST TRACK]</b>\n" if is_fast_track else "🟡 <b>הזדמנות חדשה זוהתה</b>\n"
    type_title = "🏛️ <b>מכרז ציבורי</b>" if is_tender else "🔨 <b>ליד פרטי</b>"

    title = html.escape(str(opportunity_data.get("title") or "ללא כותרת"))
    location = html.escape(str(opportunity_data.get("location") or "ארצי / לא צוין"))
    work_type = html.escape(str(opportunity_data.get("work_type") or "כללי"))
    budget = opportunity_data.get("budget_value")
    budget_str = f"{budget:,.0f} ₪" if budget is not None else "לא צוין"

    deadline = html.escape(str(opportunity_data.get("deadline") or "לא הוגדר"))
    score = opportunity_data.get("score_business_fit", 0)
    source_url = opportunity_data.get("source_url")

    lines = [
        badge,
        f"{type_title}: <b>{title}</b>",
        "",
        f"📍 <b>מיקום:</b> {location}",
        f"🛠️ <b>מקצוע:</b> {work_type}",
        f"💰 <b>תקציב:</b> {budget_str}",
        f"📅 <b>מועד אחרון:</b> {deadline}",
        f"🎯 <b>ציון התאמה:</b> {score}/100",
    ]

    tender_num = opportunity_data.get("tender_number")
    if tender_num:
        lines.append(f"📑 <b>מספר מכרז:</b> {html.escape(str(tender_num))}")

    publisher = opportunity_data.get("publisher_name")
    if publisher:
        lines.append(f"🏢 <b>גוף מפרסם:</b> {html.escape(str(publisher))}")

    if source_url:
        lines.append(f"\n🔗 <a href='{source_url}'>קישור ישיר למקור</a>")

    message_text = "\n".join(lines)
    return await send_telegram_message(chat_id=chat_id, text=message_text)


async def send_daily_report_telegram(report_summary: str) -> bool:
    """שליחת תקציר דוח יומי לטלגרם."""
    chat_id = settings.telegram_chat_id
    if not chat_id:
        return False

    text = f"📊 <b>דוח יומי מסכם — לידים ומכרזים</b>\n\n{report_summary}"
    return await send_telegram_message(chat_id=chat_id, text=text)
