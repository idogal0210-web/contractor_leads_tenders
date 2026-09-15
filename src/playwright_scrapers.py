"""
src/playwright_scrapers.py — מנוע סריקת לידים מתקדם מבוסס Playwright.
עוקף חסימות בוטים, מאפשר טעינת עמודים דינמיים, גלילה וסריקת לוחות דרושים וקבוצות פייסבוק ציבוריות.
"""
import asyncio
import re
from datetime import datetime, timezone
from typing import Any, List
from playwright.async_api import async_playwright

KEYWORD_SIGNALS = [
    "מחפש קבלן", "דרוש קבלן", "קבלן שיפוצים", "שיפוץ חדר", "החלפת צנרת",
    "אינסטלטור", "עבודות חשמל", "צבע וטיח", "ריצוף", "הריסה ובנייה",
    "קבלן משנה", "דרושים עובדים", "הצעת מחיר", "איטום גג", "מיזוג"
]


async def _run_playwright_scraper(url: str, selector: str, source_name: str) -> List[dict[str, Any]]:
    """
    פונקציית תשתית גנרית לפתיחת דפדפן אנונימי (Headless), ניווט לכתובת,
    ושליפת טקסטים מאלמנטים מסוימים כדי לאתר לידים.
    """
    leads = []
    print(f"[*] פותח דפדפן Headless לסריקת {source_name} בכתובת: {url}")
    
    try:
        async with async_playwright() as p:
            # שימוש בדפדפן Chromium עם הגדרות העוקפות חסימות בסיסיות
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()
            
            # ניווט והמתנה לטעינת העמוד
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # המתנה קלה או גלילה למטה כדי לעורר טעינת Lazy Loading
            await page.evaluate("window.scrollBy(0, 1000)")
            await page.wait_for_timeout(2000)
            
            # חילוץ האלמנטים המכילים משרות או פוסטים
            elements = await page.query_selector_all(selector)
            
            for el in elements[:15]:
                text = await el.inner_text()
                if not text:
                    continue
                
                # בדיקת היתכנות לקיום ליד
                if any(kw in text for kw in KEYWORD_SIGNALS):
                    date_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")
                    leads.append({
                        "content": text.strip(),
                        "title": "ליד מלוח מקצועי: " + text.strip()[:40] + "...",
                        "source_name": source_name,
                        "url": url,
                        "source_label": f"{source_name} — נסרק ב-{date_str}",
                        "published_at": datetime.now(timezone.utc).isoformat(),
                        "discovered_at": datetime.now(timezone.utc).isoformat()
                    })
            
            await browser.close()
    except Exception as exc:
        print(f"[-] שגיאה בסריקת Playwright עבור {source_name}: {exc}")
        
    print(f"[+] נסרקו בהצלחה {len(leads)} לידים חדשים מתוך {source_name}")
    return leads


def fetch_job_boards() -> list[dict[str, Any]]:
    """סריקת לוחות דרושים ועבודה מקצועיים (קריאה סינכרונית שעוטפת את Playwright)."""
    # דוגמה לכתובת חיפוש כללית בלוח דרושים (ניתן להחליף ב-URL אמיתי של AllJobs/Drushim/Yad2)
    job_board_url = "https://www.example.com/jobs/search?q=קבלן+שיפוצים"
    # הסלקטור משתנה בהתאם לאתר האמיתי, לדוגמה: div.job-card או article.post
    selector = "div, article" 
    
    # הפעלת הלולאה האסינכרונית (שימו לב: מכיוון ש-fetchers נקראים מקוד סינכרוני, נשתמש ב-asyncio.run)
    try:
        leads = asyncio.run(_run_playwright_scraper(job_board_url, selector, "לוח דרושים (Playwright)"))
        return leads
    except Exception as e:
        print(f"[-] תקלה בסריקת לוחות דרושים: {e}")
        return []


def fetch_facebook_groups() -> list[dict[str, Any]]:
    """סריקת קבוצות פייסבוק פומביות (דורש דפדפן אמיתי כדי לטעון JS)."""
    # כתובת לקבוצת פייסבוק פומבית (לדוגמה קבוצת "קבלני שיפוצים")
    fb_group_url = "https://www.facebook.com/groups/example_group"
    # פייסבוק משתמשת בסלקטורים מורכבים. "div[role='article']" בדרך כלל לוכד פוסטים
    selector = "div[role='article']"
    
    try:
        leads = asyncio.run(_run_playwright_scraper(fb_group_url, selector, "קבוצת פייסבוק (Playwright)"))
        return leads
    except Exception as e:
        print(f"[-] תקלה בסריקת פייסבוק: {e}")
        return []
