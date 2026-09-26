import asyncio
from datetime import datetime, timezone
import structlog
from typing import List, Dict, Any
from playwright.async_api import async_playwright

log = structlog.get_logger(__name__)

async def _authenticated_scrape() -> List[Dict[str, Any]]:
    """
    2. סריקת עומק מאומתת (Authenticated DOM Parsing) - ללוחות B2B סגורים
    במקרה הזה: יפעת מכרזים (קטגוריית בינוי) - tenders.co.il
    """
    leads = []
    url = "https://www.tenders.co.il/Category/20210000/building/cat"
    log.info(f"Starting DOM Parsing for B2B portal: {url}")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            page = await context.new_page()
            
            # Navigate and wait for React to render the tender list
            await page.goto(url, timeout=60000)
            
            # Wait for at least one tender row to appear (using a CSS attribute selector for dynamic React classes)
            await page.wait_for_selector('div[class*="catRecord__tender_txt_wraper"]', timeout=15000)
            
            # Extract all tender rows
            rows = await page.query_selector_all('div[class*="catRecord__tender_txt_wraper"]')
            
            for row in rows[:20]:  # Limit to top 20 recent
                # Extract text using inner_text
                text = await row.inner_text()
                lines = [line.strip() for line in text.split('\n') if line.strip() and line.strip() != '•']
                
                if not lines:
                    continue
                    
                title = lines[0]
                date_str = lines[1] if len(lines) > 1 else ""
                
                content = f"הזדמנות B2B (יפעת מכרזים):\nפרויקט: {title}\nתאריך: {date_str}"
                
                leads.append({
                    "content": content,
                    "title": title,
                    "source_name": "יפעת מכרזים - בינוי",
                    "url": url, # Link to category page since specific tender link is premium/hidden
                    "source_label": "סריקת עומק (DOM Parsing)",
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "discovered_at": datetime.now(timezone.utc).isoformat()
                })
                
            await browser.close()
            log.info(f"Pulled {len(leads)} B2B tenders from Yifat.")
            return leads

    except Exception as e:
        log.error("b2b_authenticated_scrape_failed", error=str(e))
        return []

def fetch_b2b_portals() -> List[Dict[str, Any]]:
    return asyncio.run(_authenticated_scrape())
