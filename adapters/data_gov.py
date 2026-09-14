"""
adapters/data_gov.py
--------------------
מתאם ל-CKAN API של data.gov.il — מכרזים עירוניים.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from adapters.base import BaseAdapter, FetchResult, RawItem
from adapters.gov_tenders import _normalize_date

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# קבועים
# ---------------------------------------------------------------------------

DATA_GOV_API = "https://data.gov.il/api/3/action/datastore_search"

# TODO: יש להחליף ב-UUIDs אמיתיים מ-data.gov.il אחרי בדיקה ידנית
# ניתן למצוא ב: https://data.gov.il/dataset?tags=מכרזים
MUNICIPAL_TENDER_RESOURCE_IDS: list[str] = [
    # TODO: "REPLACE_WITH_REAL_RESOURCE_UUID_1",  # מכרזי עירייה — רשימה כללית
    # TODO: "REPLACE_WITH_REAL_RESOURCE_UUID_2",  # מכרזי בנייה עירוניים
    # TODO: "REPLACE_WITH_REAL_RESOURCE_UUID_3",  # מכרזי תחזוקה
]

# ערים מעניינות
RELEVANT_CITIES: frozenset[str] = frozenset(
    [
        "נתניה",
        "תל אביב",
        "תל-אביב",
        "פתח תקווה",
        "פתח-תקווה",
        "חולון",
        "ראשון לציון",
        "ראשון-לציון",
        "חיפה",
        "בת ים",
        "בת-ים",
        "רמת גן",
        "רמת-גן",
    ]
)

_REQUEST_TIMEOUT = 30.0
_PAGE_SIZE = 100


# ---------------------------------------------------------------------------
# מתאם
# ---------------------------------------------------------------------------


class DataGovAdapter(BaseAdapter):
    """
    שולף מכרזים עירוניים מ-CKAN datastore של data.gov.il.

    מסנן לפי רשימת ערים מוגדרת.
    """

    source_name = "data.gov.il"

    def __init__(
        self,
        resource_ids: list[str] | None = None,
        cities: list[str] | None = None,
        page_size: int = _PAGE_SIZE,
        timeout: float = _REQUEST_TIMEOUT,
    ) -> None:
        # אם לא סופקו resource IDs — נשתמש ברשימת ברירת המחדל
        self._resource_ids = resource_ids or MUNICIPAL_TENDER_RESOURCE_IDS
        self._cities = frozenset(cities) if cities else RELEVANT_CITIES
        self._page_size = page_size
        self._timeout = timeout

    # -----------------------------------------------------------------------
    # ממשק מופשט
    # -----------------------------------------------------------------------

    async def fetch(self) -> FetchResult:
        """שליפת מכרזים עירוניים מכל resource IDs המוגדרים."""
        if not self._resource_ids:
            log.warning("data_gov_no_resource_ids", hint="Add real resource IDs to MUNICIPAL_TENDER_RESOURCE_IDS")
            return FetchResult.no_results(self.source_name)

        all_items: list[RawItem] = []

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout),
            headers={"Accept": "application/json", "User-Agent": "LeadsTenders/1.0"},
            follow_redirects=True,
        ) as client:
            for resource_id in self._resource_ids:
                try:
                    records = await self._fetch_resource(client, resource_id)
                except httpx.TimeoutException as exc:
                    log.warning("data_gov_timeout", resource_id=resource_id, error=str(exc))
                    continue
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    if status == 429:
                        log.warning("data_gov_rate_limit", resource_id=resource_id)
                        return FetchResult.failed(self.source_name, "rate_limit", "HTTP 429")
                    log.error("data_gov_http_error", resource_id=resource_id, status=status)
                    continue
                except httpx.HTTPError as exc:
                    log.error("data_gov_http_error", resource_id=resource_id, error=str(exc))
                    continue

                for record in records:
                    item = self._parse_record(record)
                    if item is not None:
                        all_items.append(item)

        if not all_items:
            return FetchResult.no_results(self.source_name)

        log.info("data_gov_fetched", total=len(all_items))
        return FetchResult(success=True, items=all_items, source_name=self.source_name)

    # -----------------------------------------------------------------------
    # שליפת resource בודד (עם pagination)
    # -----------------------------------------------------------------------

    async def _fetch_resource(
        self,
        client: httpx.AsyncClient,
        resource_id: str,
    ) -> list[dict[str, Any]]:
        """
        שולף את כל הרשומות של resource_id אחד.
        משתמש ב-offset לסריקת כל העמודים.
        """
        all_records: list[dict[str, Any]] = []
        offset = 0

        while True:
            params = {
                "resource_id": resource_id,
                "limit": self._page_size,
                "offset": offset,
            }

            resp = await client.get(DATA_GOV_API, params=params)
            resp.raise_for_status()

            body = resp.json()

            if not body.get("success"):
                error_msg = body.get("error", {}).get("message", "Unknown CKAN error")
                log.warning("data_gov_ckan_error", resource_id=resource_id, error=error_msg)
                break

            records: list[dict[str, Any]] = body.get("result", {}).get("records", [])

            if not records:
                break

            all_records.extend(records)

            if len(records) < self._page_size:
                break

            offset += self._page_size

        log.debug("data_gov_resource_fetched", resource_id=resource_id, count=len(all_records))
        return all_records

    # -----------------------------------------------------------------------
    # עיבוד רשומה בודדת
    # -----------------------------------------------------------------------

    def _parse_record(self, record: dict[str, Any]) -> RawItem | None:
        """
        ממיר רשומת CKAN ל-RawItem.
        מחזיר None אם העיר לא בתחום העניין.
        """
        # שמות שדות אפשריים ב-CKAN datasets שונים
        city: str = (
            record.get("city", "")
            or record.get("municipality", "")
            or record.get("עיר", "")
            or record.get("רשות", "")
            or ""
        )

        if not self._is_relevant_city(city):
            return None

        title: str = (
            record.get("tender_name", "")
            or record.get("name", "")
            or record.get("שם", "")
            or record.get("תיאור", "")
            or ""
        )
        description: str = (
            record.get("description", "")
            or record.get("תיאור_מלא", "")
            or ""
        )
        tender_id: str = str(
            record.get("tender_id", "")
            or record.get("מזהה", "")
            or record.get("_id", "")
        )
        publish_date: str | None = (
            record.get("publish_date")
            or record.get("תאריך_פרסום")
            or record.get("date")
        )
        close_date: str | None = (
            record.get("close_date")
            or record.get("תאריך_סגירה")
            or record.get("closing_date")
        )

        content_parts = [
            f"כותרת: {title}",
            f"עיר: {city}",
            f"תיאור: {description}",
        ]
        if tender_id:
            content_parts.append(f"מזהה מכרז: {tender_id}")
        if close_date:
            content_parts.append(f"תאריך סגירה: {close_date}")

        content = "\n".join(filter(None, content_parts))

        return RawItem(
            content=content,
            url=record.get("url") or record.get("link"),
            published_at=_normalize_date(publish_date),
            item_type="tender",
            metadata={
                "source": "data.gov.il",
                "city": city,
                "tender_id": tender_id,
                "raw": record,
            },
        )

    # -----------------------------------------------------------------------
    # עזר פנימי
    # -----------------------------------------------------------------------

    def _is_relevant_city(self, city: str) -> bool:
        """בדיקה אם העיר נמצאת ברשימת הערים הרלוונטיות."""
        if not city:
            return False
        return any(c in city for c in self._cities)
