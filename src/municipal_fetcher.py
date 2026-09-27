import asyncio
from datetime import datetime, timezone
import structlog
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from google import genai
from pydantic import BaseModel, Field
from config.settings import settings
from tenacity import retry, wait_exponential, stop_after_attempt

log = structlog.get_logger(__name__)

MUNICIPALITIES = [
    {"name": "עיריית תל אביב", "url": "https://www.tel-aviv.gov.il/Residents/Tenders/Pages/default.aspx"},
    {"name": "עיריית פתח תקווה", "url": "https://www.petah-tikva.muni.il/tenders/"},
    {"name": "עיריית חולון", "url": "https://www.holon.muni.il/tenders/"},
    {"name": "עיריית ראשון לציון", "url": "https://www.rishonlezion.muni.il/tenders/"},
    {"name": "עיריית רמת גן", "url": "https://www.ramat-gan.muni.il/tenders/"}
]

class MunicipalTender(BaseModel):
    title: str = Field(description="כותרת המכרז / שם הפרויקט")
    description: str = Field(description="תיאור תמציתי של מהות המכרז מתוך הטקסט")
    date_info: str = Field(description="מועדי הגשה, סיור קבלנים או תאריך פרסום")
    is_construction_or_earthworks: bool = Field(description="האם זה קשור לעבודות קבלניות, בינוי, פיתוח, תשתיות או עבודות עפר? (True/False)")

class MunicipalTenderList(BaseModel):
    tenders: list[MunicipalTender]

async def _fetch_municipality_page(name: str, url: str) -> str:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(4000) # Let angular/react load fully
            
            await page.evaluate('''() => {
                document.querySelectorAll('script, style, noscript, iframe, nav, footer, header').forEach(el => el.remove());
            }''')
            
            text = await page.locator("body").inner_text()
            await browser.close()
            return text
    except Exception as e:
        log.warning(f"Failed to fetch {name} at {url}", error=str(e))
        return ""

@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
def extract_with_llm(client, prompt: str):
    return client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": MunicipalTenderList,
            "temperature": 0.1
        }
    )

async def _municipalities_scrape() -> List[Dict[str, Any]]:
    leads = []
    client = genai.Client(api_key=settings.gemini_api_key)
    
    for muni in MUNICIPALITIES:
        log.info(f"Scanning municipal tenders for {muni['name']}...")
        page_text = await _fetch_municipality_page(muni["name"], muni["url"])
        
        if not page_text or len(page_text) < 50:
            continue
            
        prompt = (
            f"הנה טקסט מעמוד המכרזים של {muni['name']}.\n"
            f"חלץ את כל המכרזים שמופיעים בו.\n\n"
            f"טקסט:\n{page_text[:15000]}"
        )
        
        try:
            res = extract_with_llm(client, prompt)
            extracted_list = MunicipalTenderList.model_validate_json(res.text)
            
            for t in extracted_list.tenders:
                if t.is_construction_or_earthworks:
                    content = (
                        f"מכרז מוניציפלי מתוך אתר {muni['name']}:\n"
                        f"כותרת: {t.title}\n"
                        f"תיאור: {t.description}\n"
                        f"תאריכים: {t.date_info}"
                    )
                    leads.append({
                        "content": content,
                        "title": t.title,
                        "source_name": muni["name"],
                        "url": muni["url"],
                        "source_label": "אתר עירייה רשמי (סריקה ישירה)",
                        "published_at": datetime.now(timezone.utc).isoformat(),
                        "discovered_at": datetime.now(timezone.utc).isoformat()
                    })
                    
        except Exception as e:
            log.warning(f"Failed LLM extraction for {muni['name']}", error=str(e))
            
    log.info(f"Pulled total {len(leads)} tenders from 5 Municipalities.")
    return leads

def fetch_municipal_tenders() -> List[Dict[str, Any]]:
    return asyncio.run(_municipalities_scrape())
