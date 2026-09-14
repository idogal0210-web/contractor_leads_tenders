"""
adapters/municipal_scraper.py
-----------------------------
מגרד Playwright לאתרי עיריות ישראליות — שליפת מכרזים.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from adapters.base import BaseAdapter, FetchResult, RawItem
from adapters.gov_tenders import _normalize_date

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# הגדרות ערים
# ---------------------------------------------------------------------------

MUNICIPAL_SOURCES: list[dict[str, str]] = [
    {
        "name": "תל אביב",
        "url": "https://www.tel-aviv.gov.il/Residents/Tenders/Pages/default.aspx",
        "parser": "tel_aviv",
    },
    {
        "name": "נתניה",
        "url": "https://www.netanya.muni.il/Residents/Tenders",
        "parser": "generic_table",
    },
    {
        "name": "פתח תקווה",
        "url": "https://www.petahtikva.muni.il/tenders",
        "parser": "generic_table",
    },
    {
        "name": "חולון",
        "url": "https://www.holon.muni.il/tenders",
        "parser": "generic_table",
    },
    {
        "name": "ראשון לציון",
        "url": "https://www.rishon-lezion.muni.il/tenders",
        "parser": "generic_table",
    },
    {
        "name": "חיפה",
        "url": "https://www.haifa.muni.il/tenders",
        "parser": "generic_table",
    },
]

_BROWSER_TIMEOUT = 30_000    # ms — זמן המתנה לטעינת דף
_NAV_TIMEOUT = 45_000        # ms — זמן המתנה לניווט
_MAX_RETRIES = 3
_RETRY_WAIT_MIN = 2          # שניות
_RETRY_WAIT_MAX = 10         # שניות


# ---------------------------------------------------------------------------
# מתאם ראשי
# ---------------------------------------------------------------------------


class MunicipalScraperAdapter(BaseAdapter):
    """
    מגרד Playwright לאתרי עיריות.

    מטפל ב-6 ערים בנפרד עם לוגיקת parse מותאמת לכל עיר.
    מממש retry עם exponential back-off דרך tenacity.
    """

    source_name = "municipal_scraper"

    def __init__(
        self,
        cities: list[dict[str, str]] | None = None,
        headless: bool = True,
        timeout_ms: int = _BROWSER_TIMEOUT,
    ) -> None:
        self._cities = cities or MUNICIPAL_SOURCES
        self._headless = headless
        self._timeout_ms = timeout_ms

    # -----------------------------------------------------------------------
    # ממשק מופשט
    # -----------------------------------------------------------------------

    async def fetch(self) -> FetchResult:
        """
        סריקת כל ערי המקור בנפרד.
        מצרף את כל הפריטים לתוצאה אחת מאוחדת.
        """
        try:
            from playwright.async_api import async_playwright  # noqa: PLC0415
        except ImportError:
            log.error("playwright_not_installed", hint="pip install playwright && playwright install chromium")
            return FetchResult.failed(
                self.source_name, "fetch_failed", "playwright not installed"
            )

        all_items: list[RawItem] = []
        errors: list[str] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self._headless)

            try:
                for city_conf in self._cities:
                    try:
                        items = await self._scrape_city(browser, city_conf)
                        all_items.extend(items)
                        log.info(
                            "city_scraped",
                            city=city_conf["name"],
                            count=len(items),
                        )
                    except Exception as exc:
                        errors.append(f"{city_conf['name']}: {exc}")
                        log.error(
                            "city_scrape_error",
                            city=city_conf["name"],
                            error=str(exc),
                            exc_info=True,
                        )
            finally:
                await browser.close()

        if not all_items and errors:
            return FetchResult.failed(
                self.source_name,
                "fetch_failed",
                f"All cities failed: {'; '.join(errors)}",
            )

        if not all_items:
            return FetchResult.no_results(self.source_name)

        log.info("municipal_scraper_complete", total=len(all_items), cities=len(self._cities))
        return FetchResult(success=True, items=all_items, source_name=self.source_name)

    # -----------------------------------------------------------------------
    # סריקת עיר בודדת עם retry
    # -----------------------------------------------------------------------

    async def _scrape_city(
        self,
        browser: Any,
        city_conf: dict[str, str],
    ) -> list[RawItem]:
        """
        מגרד עיר בודדת עם retry אוטומטי.
        """
        city_name = city_conf["name"]
        url = city_conf["url"]
        parser_name = city_conf.get("parser", "generic_table")

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(_MAX_RETRIES),
            wait=wait_exponential(min=_RETRY_WAIT_MIN, max=_RETRY_WAIT_MAX),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        ):
            with attempt:
                log.debug("scrape_city_attempt", city=city_name, url=url)
                page = await browser.new_page()
                try:
                    await page.goto(url, timeout=_NAV_TIMEOUT, wait_until="networkidle")
                    rows = await self._extract_rows(page, parser_name)
                    return [
                        self._row_to_raw_item(row, city_name, url)
                        for row in rows
                        if row.get("title")
                    ]
                finally:
                    await page.close()

        return []  # לא יגיע לכאן — tenacity יזרוק

    # -----------------------------------------------------------------------
    # חילוץ שורות לפי סוג ה-parser
    # -----------------------------------------------------------------------

    async def _extract_rows(self, page: Any, parser_name: str) -> list[dict[str, Any]]:
        """מפנה לפונקציית parse מתאימה לפי שם ה-parser."""
        if parser_name == "tel_aviv":
            return await self._parse_tel_aviv(page)
        return await self._parse_generic_table(page)

    async def _parse_tel_aviv(self, page: Any) -> list[dict[str, Any]]:
        """
        Parser מותאם לאתר עיריית תל אביב (SharePoint-based).
        ממתין לרשימת items לפני חילוץ.
        """
        rows: list[dict[str, Any]] = []

        try:
            # ממתין לאלמנט הרשימה הספציפי של תל-אביב
            await page.wait_for_selector("table.ms-listviewtable, ul.tenders-list, .tender-item", timeout=self._timeout_ms)

            # ניסיון לחלץ מ-table
            table_rows = await page.query_selector_all("table.ms-listviewtable tr:not(:first-child)")

            if table_rows:
                for row in table_rows:
                    cells = await row.query_selector_all("td")
                    if len(cells) < 2:
                        continue

                    title = await _safe_inner_text(cells[0])
                    date_str = await _safe_inner_text(cells[1]) if len(cells) > 1 else None
                    href = await _safe_href(cells[0])

                    if title:
                        rows.append({"title": title, "date": date_str, "url": href, "category": ""})
            else:
                # fallback לרשימה
                items = await page.query_selector_all(".tender-item, li.tender")
                for item in items:
                    title = await _safe_inner_text(await item.query_selector("h2, h3, .title, a"))
                    date_str = await _safe_inner_text(await item.query_selector(".date, time"))
                    href = await _safe_href(await item.query_selector("a"))
                    if title:
                        rows.append({"title": title, "date": date_str, "url": href, "category": ""})

        except Exception as exc:
            log.warning("tel_aviv_parse_error", error=str(exc))

        return rows

    async def _parse_generic_table(self, page: Any) -> list[dict[str, Any]]:
        """
        Parser גנרי לטבלאות HTML / רשימות מכרזים סטנדרטיות.
        מנסה כמה selectors נפוצים.
        """
        rows: list[dict[str, Any]] = []

        try:
            # ממתין לטעינה ראשונית
            await page.wait_for_selector(
                "table tr, .tender-row, .tender-item, li.tender, article.tender",
                timeout=self._timeout_ms,
            )

            # חילוץ מ-table
            table_rows = await page.query_selector_all("table tbody tr, table tr:not(:first-child)")
            if table_rows:
                for row in table_rows:
                    cells = await row.query_selector_all("td")
                    if not cells:
                        continue

                    title = await _safe_inner_text(cells[0])
                    date_str = await _safe_inner_text(cells[1]) if len(cells) > 1 else None
                    category = await _safe_inner_text(cells[2]) if len(cells) > 2 else ""
                    href = await _safe_href(cells[0])

                    if title:
                        rows.append(
                            {"title": title, "date": date_str, "url": href, "category": category or ""}
                        )
                return rows

            # fallback לכרטיסיות / רשימה
            items = await page.query_selector_all(".tender-row, .tender-item, article.tender, li.tender")
            for item in items:
                title_el = await item.query_selector("h2, h3, h4, .title, a.title, a:first-child")
                date_el = await item.query_selector(".date, .publish-date, time, .tender-date")
                cat_el = await item.query_selector(".category, .cat, .tender-type")

                title = await _safe_inner_text(title_el)
                date_str = await _safe_inner_text(date_el)
                category = await _safe_inner_text(cat_el)
                href = await _safe_href(title_el or item)

                if title:
                    rows.append({"title": title, "date": date_str, "url": href, "category": category or ""})

        except Exception as exc:
            log.warning("generic_table_parse_error", error=str(exc))

        return rows

    # -----------------------------------------------------------------------
    # המרת שורה ל-RawItem
    # -----------------------------------------------------------------------

    def _row_to_raw_item(
        self,
        row: dict[str, Any],
        city_name: str,
        base_url: str,
    ) -> RawItem:
        """ממיר שורה שחולצה מהדף ל-RawItem."""
        title: str = row.get("title", "")
        date_str: str | None = row.get("date")
        category: str = row.get("category", "")
        item_url: str | None = row.get("url")

        # נרמול URL יחסי לאבסולוטי
        if item_url and item_url.startswith("/"):
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            item_url = f"{parsed.scheme}://{parsed.netloc}{item_url}"

        content_parts = [f"כותרת: {title}", f"עיר: {city_name}"]
        if category:
            content_parts.append(f"קטגוריה: {category}")
        if date_str:
            content_parts.append(f"תאריך: {date_str}")
        if item_url:
            content_parts.append(f"קישור: {item_url}")

        content = "\n".join(content_parts)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        return RawItem(
            content=content,
            url=item_url,
            published_at=_normalize_date(date_str),
            item_type="tender",
            metadata={
                "source": "municipal_scraper",
                "city": city_name,
                "category": category,
                "content_hash": content_hash,
            },
        )


# ---------------------------------------------------------------------------
# עזרי Playwright
# ---------------------------------------------------------------------------


async def _safe_inner_text(element: Any) -> str:
    """מחלץ טקסט מאלמנט Playwright — מחזיר מחרוזת ריקה אם נכשל."""
    if element is None:
        return ""
    try:
        text = await element.inner_text()
        return text.strip() if text else ""
    except Exception:
        return ""


async def _safe_href(element: Any) -> str | None:
    """מחלץ href מאלמנט — מחזיר None אם נכשל."""
    if element is None:
        return None
    try:
        # אם האלמנט עצמו הוא a-tag
        tag = await element.evaluate("el => el.tagName.toLowerCase()")
        if tag == "a":
            return await element.get_attribute("href")
        # חיפוש a-tag פנימי
        anchor = await element.query_selector("a")
        if anchor:
            return await anchor.get_attribute("href")
        return None
    except Exception:
        return None
