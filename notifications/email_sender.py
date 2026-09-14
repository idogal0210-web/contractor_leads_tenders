"""
notifications/email_sender.py — שליחת התראות ודוחות במייל (SMTP).

תומך ב-HTML RTL מעוצב, STARTTLS ואימות SMTP.
"""
from __future__ import annotations

import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import structlog
from jinja2 import Environment, FileSystemLoader

from config.settings import settings

log = structlog.get_logger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _render_template(template_name: str, context: dict[str, Any]) -> str:
    """טעינת ורינדור תבנית Jinja2 מתיקיית templates."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    template = env.get_template(template_name)
    return template.render(**context)


def _send_smtp_sync(to: str, subject: str, html_body: str, plain_body: str = "") -> bool:
    """שליחה סינכרונית דרך SMTP (רצה ב-thread pool)."""
    if not settings.smtp_user or not settings.smtp_password:
        log.warning("smtp_not_configured_skipping_send", recipient=to)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to

    if plain_body:
        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)

        log.info("email_sent_successfully", recipient=to, subject=subject)
        return True
    except Exception as exc:
        log.error("email_send_failed", recipient=to, error=str(exc))
        return False


async def send_email(to: str, subject: str, html_body: str, plain_body: str = "") -> bool:
    """שליחת אימייל אסינכרונית תוך הרצת SMTP ב-executor נפרד."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _send_smtp_sync, to, subject, html_body, plain_body)


async def send_opportunity_alert(
    opportunity_data: dict[str, Any],
    recipient_email: str,
    is_fast_track: bool = False,
) -> bool:
    """שליחת התראת ליד או מכרז בדוא"ל."""
    is_tender = opportunity_data.get("opportunity_type") == "tender"
    template_name = "tender_alert.html" if is_tender else "lead_alert.html"

    subject_prefix = "🔴 [FAST-TRACK] " if is_fast_track else "🟡 "
    type_str = "מכרז חדש" if is_tender else "ליד חדש"
    title = opportunity_data.get("title") or "ללא כותרת"
    subject = f"{subject_prefix}{type_str}: {title}"

    try:
        html_body = _render_template(
            template_name,
            {
                "opportunity": opportunity_data,
                "is_fast_track": is_fast_track,
                "is_tender": is_tender,
            },
        )
    except Exception as exc:
        log.error("render_email_template_failed", template=template_name, error=str(exc))
        html_body = f"<h2>{subject}</h2><p>{opportunity_data.get('summary', '')}</p>"

    return await send_email(to=recipient_email, subject=subject, html_body=html_body)


async def send_daily_report_email(
    report_data: dict[str, Any],
    recipient_email: str,
) -> bool:
    """שליחת הדוח היומי בדוא"ל."""
    date_str = report_data.get("date", "")
    subject = f"📊 דוח יומי — לידים ומכרזים ({date_str})"

    try:
        html_body = _render_template(
            "daily_report.html",
            {"report": report_data},
        )
    except Exception as exc:
        log.error("render_daily_report_template_failed", error=str(exc))
        html_body = f"<h2>{subject}</h2><pre>{report_data}</pre>"

    return await send_email(to=recipient_email, subject=subject, html_body=html_body)
