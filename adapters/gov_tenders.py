"""
adapters/gov_tenders.py
-----------------------
מתאם ל-API המכרזים של gov.il.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

from adapters.base import BaseAdapter, FetchResult, RawItem

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# קבועים
# ---------------------------------------------------------------------------

GOV_TENDERS_API = "https://www.gov.il/api/tenders"

# קטגוריות רלוונטיות לקבלני בניין
RELEVANT_CATEGORIES: frozenset[str] = frozenset(
    [
        "בנייה",
        "תשתיות",
        "חשמל",
        "אינסטלציה",
        "שיפוץ",
        "תחזוקה",
        "עבודות עפר",
        "צנרת",
        "ריצוף",
        "גמר",
        "מיזוג אוויר",
        "הנדסה",
    ]
)

_REQUEST_TIMEOUT = 30.0       # שניות
_PAGE_SIZE = 100              # פריטים לעמוד


# ---------------------------------------------------------------------------
# מתאם
# ---------------------------------------------------------------------------


class GovTendersAdapter(BaseAdapter):
    """
    שולף מכרזים ממערכת המכרזים הממשלתית (gov.il).

    מסנן לפי קטגוריות הרלוונטיות לקבלני בנייה.
    """

    source_name = "gov.il/tenders"

    def __init__(
        self,
        categories: list[str] | None = None,
        page_size: int = _PAGE_SIZE,
        timeout: float = _REQUEST_TIMEOUT,
    ) -> None:
        self._categories = frozenset(categories) if categories else RELEVANT_CATEGORIES
        self._page_size = page_size
        self._timeout = timeout

    # -----------------------------------------------------------------------
    # ממשק מופשט
    # -----------------------------------------------------------------------

    async def fetch(self) -> FetchResult:
        """שליפת מכרזים עדכניים מ-gov.il ועיבודם ל-RawItem."""
        items: list[RawItem] = []

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout),
            headers={"Accept": "application/json", "User-Agent": "LeadsTenders/1.0"},
            follow_redirects=True,
        ) as client:
            try:
                raw_tenders = await self._fetch_all_pages(client)
            except httpx.TimeoutException as exc:
                log.warning("gov_tenders_timeout", error=str(exc))
                return FetchResult.failed(self.source_name, "fetch_failed", f"Timeout: {exc}")
            except httpx.HTTPStatusError as exc:
                return self._handle_http_status_error(exc)
            except httpx.HTTPError as exc:
                log.error("gov_tenders_http_error", error=str(exc))
                return FetchResult.failed(self.source_name, "fetch_failed", str(exc))

        if not raw_tenders:
            return FetchResult.no_results(self.source_name)

        for tender in raw_tenders:
            item = self._parse_tender(tender)
            if item is not None:
                items.append(item)

        log.info(
            "gov_tenders_fetched",
            total=len(raw_tenders),
            filtered=len(items),
        )

        return FetchResult(success=True, items=items, source_name=self.source_name)

    # -----------------------------------------------------------------------
    # שליפת עמודים
    # -----------------------------------------------------------------------

    async def _fetch_all_pages(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """
        שולף את כל עמודי התוצאות (pagination).
        עוצר כשמקבל עמוד ריק.
        """
        all_tenders: list[dict[str, Any]] = []
        skip = 0

        while True:
            params = {
                "limit": self._page_size,
                "skip": skip,
                "sortby": "publishDate",
                "order": "desc",
            }

            resp = await client.get(GOV_TENDERS_API, params=params)
            resp.raise_for_status()

            data = resp.json()
            # מבנה JSON: {"results": [...], "total": N}
            # (תואם את ה-API הנוכחי של gov.il — עשוי להשתנות)
            results: list[dict[str, Any]] = data.get("results") or data if isinstance(data, list) else []

            if not results:
                break

            all_tenders.extend(results)

            if len(results) < self._page_size:
                # עמוד חלקי — אין עוד עמודים
                break

            skip += self._page_size

        return all_tenders

    # -----------------------------------------------------------------------
    # עיבוד פריט בודד
    # -----------------------------------------------------------------------

    def _parse_tender(self, tender: dict[str, Any]) -> RawItem | None:
        """
        ממיר מכרז גולמי ל-RawItem.
        מחזיר None אם הקטגוריה לא רלוונטית.
        """
        category: str = (
            tender.get("category", "")
            or tender.get("CategoryDesc", "")
            or tender.get("tenderType", "")
        )

        # סינון לפי קטגוריה
        if not self._is_relevant_category(category):
            return None

        title: str = (
            tender.get("tenderName", "")
            or tender.get("title", "")
            or tender.get("TenderName", "")
        )
        description: str = (
            tender.get("description", "")
            or tender.get("tenderDescription", "")
            or ""
        )
        tender_id: str = str(
            tender.get("tenderId", "")
            or tender.get("TenderId", "")
            or tender.get("id", "")
        )
        publish_date: str | None = (
            tender.get("publishDate")
            or tender.get("PublishDate")
            or tender.get("startDate")
        )

        # בניית URL לפריט
        url: str | None = (
            tender.get("url")
            or (
                f"https://www.gov.il/he/departments/legalinfo/{tender_id}"
                if tender_id
                else None
            )
        )

        # תאריך בפורמט ISO
        published_at: str | None = _normalize_date(publish_date)

        # הרכבת תוכן טקסטואלי מובנה לצינור עיבוד הבא
        content_parts = [
            f"כותרת: {title}",
            f"קטגוריה: {category}",
            f"תיאור: {description}",
            f"מזהה מכרז: {tender_id}",
        ]
        if tender.get("closingDate") or tender.get("ClosingDate"):
            content_parts.append(
                f"תאריך סגירה: {tender.get('closingDate') or tender.get('ClosingDate')}"
            )
        if tender.get("publishingBody") or tender.get("PublishingBody"):
            content_parts.append(
                f"גוף מפרסם: {tender.get('publishingBody') or tender.get('PublishingBody')}"
            )

        content = "\n".join(content_parts)

        return RawItem(
            content=content,
            url=url,
            published_at=published_at,
            item_type="tender",
            metadata={
                "source": "gov.il",
                "tender_id": tender_id,
                "category": category,
                "raw": tender,
            },
        )

    # -----------------------------------------------------------------------
    # עזרים פנימיים
    # -----------------------------------------------------------------------

    def _is_relevant_category(self, category: str) -> bool:
        """בדיקה אם הקטגוריה רלוונטית לקבלנות בנייה."""
        if not category:
            return False
        category_lower = category.lower()
        return any(
            cat.lower() in category_lower for cat in self._categories
        )

    @staticmethod
    def _handle_http_status_error(exc: httpx.HTTPStatusError) -> FetchResult:
        """ממפה שגיאות HTTP לסוגי שגיאה של FetchResult."""
        status = exc.response.status_code
        source = "gov.il/tenders"

        if status == 404:
            log.warning("gov_tenders_404")
            return FetchResult.no_results(source)
        if status == 401:
            log.error("gov_tenders_auth_error", status=status)
            return FetchResult.failed(source, "auth_error", f"HTTP {status}")
        if status == 429:
            log.warning("gov_tenders_rate_limit")
            return FetchResult.failed(source, "rate_limit", f"HTTP {status} — Too Many Requests")

        log.error("gov_tenders_http_status_error", status=status)
        return FetchResult.failed(source, "fetch_failed", f"HTTP {status}: {exc.response.text[:200]}")


# ---------------------------------------------------------------------------
# פונקציות עזר
# ---------------------------------------------------------------------------


def _normalize_date(raw: str | None) -> str | None:
    """מנסה להמיר תאריך גולמי לפורמט ISO-8601."""
    if not raw:
        return None

    # אם כבר ב-ISO — מחזיר כמות שהוא
    if "T" in raw or raw.count("-") >= 2:
        return raw

    # פורמטים נפוצים בממשלה הישראלית
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            continue

    return raw  # מחזיר גולמי אם לא הצליח
