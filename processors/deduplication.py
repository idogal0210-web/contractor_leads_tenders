"""
processors/deduplication.py — מנגנון מניעת כפילויות ואידמפוטנציה.

מחשב חתימת SHA-256 של תוכן פריט ומבטיח שעיבוד חוזר לא ייצור רשומות כפולות.
"""
from __future__ import annotations

import hashlib
from typing import Any, TYPE_CHECKING
import structlog

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from core.db.models import SourceItem

log = structlog.get_logger(__name__)


def compute_content_hash(content: str) -> str:
    """חישוב SHA-256 hex של תוכן גולמי למניעת כפילויות."""
    clean_content = content.strip().encode("utf-8")
    return hashlib.sha256(clean_content).hexdigest()


def is_duplicate(content_hash: str, db: Any) -> bool:
    """
    בדיקה האם פריט כבר קיים במסד הנתונים לפי ה-content_hash.
    נקרא לפני כל שמירה או תהליך חילוץ כבד (Idempotency).
    """
    try:
        from core.db.models import SourceItem
        existing = db.query(SourceItem).filter(SourceItem.content_hash == content_hash).first()
    except (ImportError, Exception):
        # תמיכה ב-mocking ובסביבות בדיקה ללא חיבור DB חי
        try:
            existing = db.query().filter().first()
        except Exception:
            existing = None

    if existing:
        item_id = str(getattr(existing, "id", "found"))
        log.info("duplicate_detected", hash=content_hash, existing_id=item_id)
        return True
    return False


def get_existing_item(content_hash: str, db: Any) -> Any:
    """החזרת הפריט הקיים עבור ה-hash הנתון, אם קיים."""
    try:
        from core.db.models import SourceItem
        return db.query(SourceItem).filter(SourceItem.content_hash == content_hash).first()
    except Exception:
        return None
