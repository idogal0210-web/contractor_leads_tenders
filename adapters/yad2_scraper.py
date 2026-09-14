"""
adapters/yad2_scraper.py — סקרייפר ללידים פרטיים ולוחות דרישת שירות (Yad2 / פורומי שיפוץ).

סורק בקשות שירות והצעות עבודה פרטיות עם Playwright במצב headless.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
import structlog
from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential

from adapters.base import BaseAdapter, FetchResult, RawItem

log = structlog.get_logger(__name__)

# מקורות לידים פרטיים
PRIVATE_LEAD_SOURCES = [
    {
        "name": "פורום שיפוצים ובנייה",
        "url": "https://www.tapuz.co.il/forums/שיפוץ-ובניה.342/",
        "type": "forum",
    },
    {
        "name": "לוח עבודות ושיפוצים",
        "url": "https://www.midrag.co.il/content/tips",
        "type": "board",
    },
]

KEYWORDS_SERVICE_REQUEST = [
    "מחפש קבלן", "דרוש קבלן", "צריך שיפוץ", "עבודות חשמל",
    "אינסטלציה", "מחפש אינסטלטור", "צבע וטיח", "איטום", "עבודות עפר",
    "הצעת מחיר", "פירוק ובנייה", "קבלן משנה", "מזגנים"
]


class Yad2ScraperAdapter(BaseAdapter):
    """מתאם סריקה ללידים פרטיים ולוחות בעלי איתותי ביקוש."""
    source_name = "yad2_private_leads"

    def __init__(self, sources: list[dict[str, Any]] | None = None) -> None:
        self.sources = sources or PRIVATE_LEAD_SOURCES

    async def fetch(self) -> FetchResult:
        """סריקת מקורות לידים פרטיים."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            log.warning("playwright_not_installed", hint="pip install playwright && playwright install chromium")
            return FetchResult.failed(
                source_name=self.source_name,
                error_type="fetch_failed",
                detail="Playwright is not installed in the environment."
            )

        items: list[RawItem] = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                    locale="he-IL",
                )
                page = await context.new_page()

                for src in self.sources:
                    name = src["name"]
                    url = src["url"]
                    log.info("scraping_private_source", source=name, url=url)

                    try:
                        async for attempt in AsyncRetrying(
                            stop=stop_after_attempt(2),
                            wait=wait_exponential(multiplier=1, min=2, max=5),
                            reraise=True,
                        ):
                            with attempt:
                                await page.goto(url, timeout=25000, wait_until="domcontentloaded")
                                await page.wait_for_timeout(2000)

                                elements = await page.query_selector_all("article, .post, .thread, h2, h3")
                                for el in elements[:15]:
                                    text = (await el.inner_text()).strip()
                                    if not text or len(text) < 20:
                                        continue

                                    if any(kw in text for kw in KEYWORDS_SERVICE_REQUEST):
                                        items.append(
                                            RawItem(
                                                content=text,
                                                url=url,
                                                published_at=datetime.now(timezone.utc).isoformat(),
                                                item_type="lead",
                                                metadata={"source_name": name, "raw_tag": "lead_candidate"},
                                            )
                                        )

                    except Exception as exc:
                        log.warning("scrape_source_item_failed", source=name, error=str(exc))
                        continue

                await browser.close()

            if not items:
                return FetchResult.no_results(source_name=self.source_name)

            log.info("private_leads_fetched", count=len(items))
            return FetchResult(success=True, items=items, source_name=self.source_name)

        except Exception as exc:
            log.error("yad2_scraper_fatal_error", error=str(exc))
            return FetchResult.failed(
                source_name=self.source_name,
                error_type="fetch_failed",
                detail=str(exc)
            )
