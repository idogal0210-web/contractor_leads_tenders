"""
src/fetchers.py — סורק מקורות רשת חיים לאיתור לידים של שיפוצים ועבודות קבלנות.
שולף בקשות שירות בזמן אמת מפורומים ולוחות פתוחים באמצעות requests ו-BeautifulSoup.
"""
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import Any, List, Dict

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
}

KEYWORD_SIGNALS = [
    "מחפש קבלן", "דרוש קבלן", "קבלן שיפוצים", "שיפוץ חדר", "החלפת צנרת",
    "אינסטלטור", "עבודות חשמל", "צבע וטיח", "ריצוף", "הריסה ובנייה",
    "קבלן משנה", "דרושים עובדים", "הצעת מחיר", "איטום גג", "מיזוג"
]

def fetch_live_web_leads() -> list[dict[str, Any]]:
    """סריקת פורומים ולוחות פתוחים לאיתור פניות חדשות."""
    leads = []
    
    # מקור 1: פורום שיפוץ ובנייה בתפוז
    tapuz_url = "https://www.tapuz.co.il/forums/שיפוץ-ובניה.342/"
    try:
        res = requests.get(tapuz_url, headers=HEADERS, timeout=12)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            threads = soup.find_all(["div", "article"], class_=re.compile("structItem|threadItem|post"))
            for t in threads[:15]:
                title_el = t.find(["a", "h3"], class_=re.compile("title|subject"))
                snippet_el = t.find(["div", "p"], class_=re.compile("snippet|body|preview"))
                title = title_el.get_text(strip=True) if title_el else ""
                snippet = snippet_el.get_text(strip=True) if snippet_el else title
                full_text = f"{title} {snippet}".strip()
                
                if any(kw in full_text for kw in KEYWORD_SIGNALS):
                    leads.append({
                        "content": full_text,
                        "title": title,
                        "source_name": "פורום שיפוץ ובנייה",
                        "url": tapuz_url,
                        "discovered_at": datetime.now(timezone.utc).isoformat()
                    })
    except Exception as exc:
        print(f"[-] Tapuz scrape notice: {exc}")

    # מקור 2: פורום עשה זאת בעצמך ושיפוצים
    diy_url = "https://www.tapuz.co.il/forums/עשה-זאת-בעצמך.774/"
    try:
        res = requests.get(diy_url, headers=HEADERS, timeout=12)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            threads = soup.find_all(["div", "article"], class_=re.compile("structItem|threadItem|post"))
            for t in threads[:15]:
                title_el = t.find(["a", "h3"], class_=re.compile("title|subject"))
                snippet_el = t.find(["div", "p"], class_=re.compile("snippet|body|preview"))
                title = title_el.get_text(strip=True) if title_el else ""
                snippet = snippet_el.get_text(strip=True) if snippet_el else title
                full_text = f"{title} {snippet}".strip()
                
                if any(kw in full_text for kw in KEYWORD_SIGNALS):
                    leads.append({
                        "content": full_text,
                        "title": title,
                        "source_name": "פורום עשה זאת בעצמך",
                        "url": diy_url,
                        "discovered_at": datetime.now(timezone.utc).isoformat()
                    })
    except Exception as exc:
        print(f"[-] DIY forum scrape notice: {exc}")

    print(f"[+] נסרקו בהצלחה {len(leads)} לידים חדשים ממקורות פתוחים")
    return leads
