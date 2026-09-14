"""
adapters/email_ingestion.py
---------------------------
מתאם IMAP לשליפת מכרזים/לידים שהגיעו באימייל.
"""

from __future__ import annotations

import email
import imaplib
import ssl
from email.header import decode_header
from email.message import Message
from typing import Any

import structlog

from adapters.base import BaseAdapter, FetchResult, RawItem

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# קבועים
# ---------------------------------------------------------------------------

_IMAP_TIMEOUT = 30       # שניות
_MAX_MESSAGES = 100      # מגביל כמות הודעות לסריקה בפעם אחת


# ---------------------------------------------------------------------------
# מתאם
# ---------------------------------------------------------------------------


class EmailIngestionAdapter(BaseAdapter):
    """
    סורק תיבת INBOX דרך IMAP ומחלץ הודעות UNSEEN.

    לאחר שליפה: מסמן את ההודעות כ-SEEN.
    תומך ב-SSL/TLS ו-STARTTLS.
    """

    source_name = "email_ingestion"

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        use_ssl: bool = True,
        mailbox: str = "INBOX",
        max_messages: int = _MAX_MESSAGES,
    ) -> None:
        from config.settings import settings  # import מאוחר למניעת circular

        self._host = host or settings.smtp_host
        self._port = port or (993 if use_ssl else 143)
        self._username = username or settings.smtp_user
        self._password = password or settings.smtp_password
        self._use_ssl = use_ssl
        self._mailbox = mailbox
        self._max_messages = max_messages

    # -----------------------------------------------------------------------
    # ממשק מופשט
    # -----------------------------------------------------------------------

    async def fetch(self) -> FetchResult:
        """
        שולף הודעות UNSEEN מה-INBOX.

        מריץ קוד synchronous חסום ב-thread executor כדי לא לחסום את event loop.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_fetch)

    # -----------------------------------------------------------------------
    # לוגיקת שליפה synchronous
    # -----------------------------------------------------------------------

    def _sync_fetch(self) -> FetchResult:
        """פעולת IMAP synchronous — מופעלת בתוך thread executor."""
        imap: imaplib.IMAP4 | imaplib.IMAP4_SSL | None = None

        try:
            imap = self._connect()
            imap.select(self._mailbox)

            # חיפוש הודעות שלא נקראו
            status, message_ids = imap.search(None, "UNSEEN")
            if status != "OK":
                log.warning("imap_search_failed", status=status)
                return FetchResult.no_results(self.source_name)

            raw_ids: list[bytes] = message_ids[0].split()
            if not raw_ids:
                log.info("imap_no_unseen_messages")
                return FetchResult.no_results(self.source_name)

            # מגביל כמות ההודעות לעיבוד
            ids_to_process = raw_ids[: self._max_messages]
            log.info("imap_unseen_found", count=len(ids_to_process), total=len(raw_ids))

            items: list[RawItem] = []

            for msg_id in ids_to_process:
                try:
                    raw_item = self._fetch_and_parse_message(imap, msg_id)
                    if raw_item is not None:
                        items.append(raw_item)
                except Exception as exc:
                    log.error("imap_message_error", msg_id=msg_id, error=str(exc))

            log.info("imap_fetch_complete", fetched=len(items))
            return FetchResult(success=True, items=items, source_name=self.source_name)

        except imaplib.IMAP4.error as exc:
            log.error("imap_protocol_error", error=str(exc))
            # אם שגיאת אימות — מחזיר auth_error
            if "AUTHENTICATIONFAILED" in str(exc).upper() or "LOGIN" in str(exc).upper():
                return FetchResult.failed(self.source_name, "auth_error", str(exc))
            return FetchResult.failed(self.source_name, "fetch_failed", str(exc))

        except ConnectionRefusedError as exc:
            log.error("imap_connection_refused", host=self._host, port=self._port)
            return FetchResult.failed(self.source_name, "fetch_failed", f"Connection refused: {exc}")

        except TimeoutError as exc:
            log.error("imap_timeout", host=self._host)
            return FetchResult.failed(self.source_name, "fetch_failed", f"Timeout: {exc}")

        except OSError as exc:
            log.error("imap_os_error", error=str(exc))
            return FetchResult.failed(self.source_name, "fetch_failed", str(exc))

        finally:
            if imap:
                try:
                    imap.logout()
                except Exception:
                    pass

    # -----------------------------------------------------------------------
    # חיבור ל-IMAP
    # -----------------------------------------------------------------------

    def _connect(self) -> imaplib.IMAP4 | imaplib.IMAP4_SSL:
        """פותח חיבור IMAP מאובטח ומתחבר עם הפרטים שהוגדרו."""
        if self._use_ssl:
            context = ssl.create_default_context()
            imap = imaplib.IMAP4_SSL(
                host=self._host,
                port=self._port,
                ssl_context=context,
            )
        else:
            imap = imaplib.IMAP4(host=self._host, port=self._port)
            # ניסיון STARTTLS אם השרת תומך
            try:
                imap.starttls()
            except imaplib.IMAP4.error:
                log.warning("starttls_not_supported", host=self._host)

        status, _ = imap.login(self._username, self._password)
        if status != "OK":
            raise imaplib.IMAP4.error(f"Login failed with status: {status}")

        log.debug("imap_connected", host=self._host, user=self._username)
        return imap

    # -----------------------------------------------------------------------
    # שליפת ועיבוד הודעה בודדת
    # -----------------------------------------------------------------------

    def _fetch_and_parse_message(
        self,
        imap: imaplib.IMAP4 | imaplib.IMAP4_SSL,
        msg_id: bytes,
    ) -> RawItem | None:
        """
        שולף הודעה אחת, מחלץ את תוכנה, ומסמן אותה כ-SEEN.
        מחזיר None אם לא הצליח לחלץ תוכן.
        """
        status, data = imap.fetch(msg_id, "(RFC822)")
        if status != "OK" or not data:
            log.warning("imap_fetch_message_failed", msg_id=msg_id, status=status)
            return None

        raw_email: bytes = data[0][1]  # type: ignore[index]
        msg: Message = email.message_from_bytes(raw_email)

        subject = _decode_header_field(msg.get("Subject", ""))
        sender = _decode_header_field(msg.get("From", ""))
        date_str = msg.get("Date", "")
        message_id = msg.get("Message-ID", "")

        # חילוץ גוף ההודעה
        body = _extract_body(msg)

        if not body and not subject:
            log.debug("imap_empty_message_skipped", msg_id=msg_id)
            return None

        # סימון כ-SEEN לאחר שליפה מוצלחת
        imap.store(msg_id, "+FLAGS", "\\Seen")

        content = _build_content(subject=subject, sender=sender, body=body, date=date_str)

        return RawItem(
            content=content,
            url=None,
            published_at=_parse_email_date(date_str),
            item_type="lead",
            metadata={
                "source": "email_ingestion",
                "subject": subject,
                "sender": sender,
                "message_id": message_id,
                "date": date_str,
            },
        )


# ---------------------------------------------------------------------------
# פונקציות עזר
# ---------------------------------------------------------------------------


def _decode_header_field(raw: str) -> str:
    """
    מפענח שדה כותרת MIME (עשוי להיות מקודד ב-Base64/QP).
    """
    if not raw:
        return ""

    decoded_parts: list[str] = []
    for part, charset in decode_header(raw):
        if isinstance(part, bytes):
            try:
                decoded_parts.append(part.decode(charset or "utf-8", errors="replace"))
            except LookupError:
                decoded_parts.append(part.decode("utf-8", errors="replace"))
        else:
            decoded_parts.append(part)

    return " ".join(decoded_parts).strip()


def _extract_body(msg: Message) -> str:
    """
    מחלץ גוף טקסט מהודעת email.

    מעדיף text/plain, fallback ל-text/html ללא תגיות.
    """
    body_plain = ""
    body_html = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))

            # דילוג על קבצים מצורפים
            if "attachment" in disposition:
                continue

            payload = part.get_payload(decode=True)
            if payload is None:
                continue

            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")

            if content_type == "text/plain" and not body_plain:
                body_plain = text
            elif content_type == "text/html" and not body_html:
                body_html = text
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if msg.get_content_type() == "text/plain":
                body_plain = text
            else:
                body_html = text

    if body_plain:
        return body_plain.strip()

    # הסרת תגיות HTML בסיסית
    if body_html:
        return _strip_html(body_html)

    return ""


def _strip_html(html: str) -> str:
    """הסרה בסיסית של תגיות HTML ללא תלות בספריות חיצוניות."""
    import re

    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _build_content(
    *,
    subject: str,
    sender: str,
    body: str,
    date: str,
) -> str:
    """בונה תוכן מובנה להמשך עיבוד."""
    parts = []
    if subject:
        parts.append(f"נושא: {subject}")
    if sender:
        parts.append(f"שולח: {sender}")
    if date:
        parts.append(f"תאריך: {date}")
    if body:
        parts.append(f"\n{body}")
    return "\n".join(parts)


def _parse_email_date(date_str: str) -> str | None:
    """ממיר תאריך מכותרת email לפורמט ISO-8601."""
    if not date_str:
        return None
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt.isoformat()
    except Exception:
        return date_str or None
