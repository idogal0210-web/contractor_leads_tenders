"""
adapters/base.py
----------------
מחלקות בסיס לכל מתאמי מקורות הנתונים.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

import structlog

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# מבני נתונים
# ---------------------------------------------------------------------------

ErrorType = Literal[
    "no_results",
    "fetch_failed",
    "auth_error",
    "rate_limit",
    "parse_error",
]


@dataclass
class RawItem:
    """פריט גולמי יחיד שנשלף ממקור נתונים."""

    content: str                        # תוכן HTML / JSON / טקסט גולמי
    url: str | None = None              # כתובת מקור הפריט
    published_at: str | None = None     # פורמט ISO-8601
    item_type: str = "lead"             # "tender" | "lead"
    metadata: dict[str, Any] = field(default_factory=dict)

    # -----------------------------------------------------------------------
    # עזרים
    # -----------------------------------------------------------------------

    @property
    def content_hash(self) -> str:
        """גיבוב SHA-256 של התוכן לצורך זיהוי כפילויות."""
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """המרה למילון לאחסון ב-DB."""
        return {
            "content": self.content,
            "url": self.url,
            "published_at": self.published_at,
            "item_type": self.item_type,
            "content_hash": self.content_hash,
            "metadata": self.metadata,
        }


@dataclass
class FetchResult:
    """תוצאת פעולת שליפה של מתאם."""

    success: bool
    items: list[RawItem] = field(default_factory=list)
    error_type: ErrorType | None = None
    error_detail: str | None = None
    source_name: str = ""

    # -----------------------------------------------------------------------
    # מאפיינים מחושבים
    # -----------------------------------------------------------------------

    @property
    def is_empty(self) -> bool:
        """המקור פעל אך לא מצא תוצאות (שונה מכשל)."""
        return self.success and len(self.items) == 0

    # -----------------------------------------------------------------------
    # בוני עזר
    # -----------------------------------------------------------------------

    @classmethod
    def no_results(cls, source_name: str) -> "FetchResult":
        """
        המקור הגיב בהצלחה אך לא נמצאו פריטים.
        נבדל מ-fetch_failed — המקור עצמו תקין.
        """
        return cls(
            success=True,
            items=[],
            error_type="no_results",
            source_name=source_name,
        )

    @classmethod
    def failed(
        cls,
        source_name: str,
        error_type: str,
        detail: str,
    ) -> "FetchResult":
        """כשל בשליפה — המקור לא הגיב כראוי."""
        return cls(
            success=False,
            error_type=error_type,  # type: ignore[arg-type]
            error_detail=detail,
            source_name=source_name,
        )

    def __repr__(self) -> str:  # noqa: D105
        status = "OK" if self.success else f"FAIL({self.error_type})"
        return (
            f"<FetchResult source={self.source_name!r} "
            f"status={status} items={len(self.items)}>"
        )


# ---------------------------------------------------------------------------
# מחלקת בסיס מופשטת
# ---------------------------------------------------------------------------


class BaseAdapter(ABC):
    """
    מחלקת בסיס מופשטת לכל מתאמי מקורות הנתונים.

    כל מתאם קונקרטי מממש :meth:`fetch`.
    השתמש ב-:meth:`_safe_fetch` בפרודקשן כדי לקבל FetchResult מובטח.
    """

    source_name: str = "base"

    # -----------------------------------------------------------------------
    # ממשק ציבורי
    # -----------------------------------------------------------------------

    @abstractmethod
    async def fetch(self) -> FetchResult:
        """
        שלוף פריטים מהמקור.

        **אסור לזרוק חריגות** — במקום זה יש להחזיר
        ``FetchResult.failed(...)`` עם פרטי השגיאה.
        """
        ...

    async def _safe_fetch(self) -> FetchResult:
        """
        עוטף את :meth:`fetch` ותופס כל חריגה בלתי-צפויה.

        מחזיר תמיד :class:`FetchResult` תקין — לעולם לא זורק.
        """
        try:
            return await self.fetch()
        except Exception as exc:
            log.error(
                "adapter_fetch_unhandled_error",
                source=self.source_name,
                error=str(exc),
                exc_info=True,
            )
            return FetchResult.failed(
                source_name=self.source_name,
                error_type="fetch_failed",
                detail=str(exc),
            )
