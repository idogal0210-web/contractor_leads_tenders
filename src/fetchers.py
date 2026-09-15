"""
src/fetchers.py — סורק מקורות רשת חיים לאיתור לידים של שיפוצים ועבודות קבלנות.
שולף בקשות שירות בזמן אמת מפורומים ולוחות פתוחים באמצעות requests ו-BeautifulSoup.
כולל חילוץ תאריך פרסום לצורך אימות אקטואליות.
"""
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from typing import Any, List, Dict, Optional

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
}

KEYWORD_SIGNALS = [
    "מחפש קבלן", "דרוש קבלן", "קבלן שיפוצים", "שיפוץ חדר", "החלפת צנרת",
    "אינסטלטור", "עבודות חשמל", "צבע וטיח", "ריצוף", "הריסה ובנייה",
    "קבלן משנה", "דרושים עובדים", "הצעת מחיר", "איטום גג", "מיזוג"
]

# סף אקטואליות — לידים ישנים מ-45 יום נפסלים
FRESHNESS_THRESHOLD_DAYS = 45

# תבניות תאריך בעברית ובאנגלית
DATE_PATTERNS = [
    # dd/mm/yyyy or dd.mm.yyyy or dd-mm-yyyy
    r'(\d{1,2})[/.\-](\d{1,2})[/.\-](20\d{2})',
    # yyyy-mm-dd (ISO)
    r'(20\d{2})-(\d{1,2})-(\d{1,2})',
]

HEBREW_MONTHS = {
    'ינואר': 1, 'פברואר': 2, 'מרץ': 3, 'אפריל': 4,
    'מאי': 5, 'יוני': 6, 'יולי': 7, 'אוגוסט': 8,
    'ספטמבר': 9, 'אוקטובר': 10, 'נובמבר': 11, 'דצמבר': 12,
}


def extract_publish_date(element, soup=None) -> Optional[datetime]:
    """
    מחלץ תאריך פרסום מאלמנט HTML.
    מחפש: תגית <time>, מטא-תגיות, וטקסט עם תבנית תאריך.
    """
    # 1. חיפוש תגית <time datetime="...">
    time_el = element.find("time")
    if time_el and time_el.get("datetime"):
        try:
            dt_str = time_el["datetime"]
            # Handle ISO format
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

    # 2. חיפוש מטא-תגיות ברמת הדף
    if soup:
        for meta_name in ["article:published_time", "datePublished", "date"]:
            meta = soup.find("meta", {"property": meta_name}) or soup.find("meta", {"name": meta_name})
            if meta and meta.get("content"):
                try:
                    return datetime.fromisoformat(meta["content"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

    # 3. חיפוש טקסט עם תבנית תאריך
    text = element.get_text()
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            try:
                if len(groups[0]) == 4:  # yyyy-mm-dd
                    return datetime(int(groups[0]), int(groups[1]), int(groups[2]), tzinfo=timezone.utc)
                else:  # dd/mm/yyyy
                    return datetime(int(groups[2]), int(groups[1]), int(groups[0]), tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue

    # 4. חיפוש תאריך עברי ("15 בספטמבר 2026")
    for month_name, month_num in HEBREW_MONTHS.items():
        heb_pattern = rf'(\d{{1,2}})\s+ב?{month_name}\s+(20\d{{2}})'
        match = re.search(heb_pattern, text)
        if match:
            try:
                return datetime(int(match.group(2)), month_num, int(match.group(1)), tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue

    return None


def is_within_freshness_threshold(pub_date: Optional[datetime], threshold_days: int = FRESHNESS_THRESHOLD_DAYS) -> bool:
    """בודק אם תאריך הפרסום בתוך חלון האקטואליות (ברירת מחדל: 45 יום)."""
    if pub_date is None:
        return True  # אם אין תאריך — לא פוסלים, ה-AI יבדוק
    now = datetime.now(timezone.utc)
    if pub_date.tzinfo is None:
        pub_date = pub_date.replace(tzinfo=timezone.utc)
    return (now - pub_date) <= timedelta(days=threshold_days)


def fetch_live_web_leads() -> list[dict[str, Any]]:
    """סריקת פורומים ולוחות פתוחים לאיתור פניות חדשות עם חילוץ תאריך."""
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
                
                # חילוץ תאריך פרסום
                pub_date = extract_publish_date(t, soup)
                
                # סינון אקטואליות — דילוג על לידים ישנים מ-45 יום
                if not is_within_freshness_threshold(pub_date):
                    continue
                
                if any(kw in full_text for kw in KEYWORD_SIGNALS):
                    pub_date_str = pub_date.strftime("%d/%m/%Y") if pub_date else datetime.now(timezone.utc).strftime("%d/%m/%Y")
                    leads.append({
                        "content": full_text,
                        "title": title,
                        "source_name": "פורום שיפוץ ובנייה",
                        "url": tapuz_url,
                        "source_label": f"פורום שיפוץ ובנייה — תפוז, פוסט מ-{pub_date_str}",
                        "published_at": pub_date.isoformat() if pub_date else None,
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
                
                pub_date = extract_publish_date(t, soup)
                
                if not is_within_freshness_threshold(pub_date):
                    continue
                
                if any(kw in full_text for kw in KEYWORD_SIGNALS):
                    pub_date_str = pub_date.strftime("%d/%m/%Y") if pub_date else datetime.now(timezone.utc).strftime("%d/%m/%Y")
                    leads.append({
                        "content": full_text,
                        "title": title,
                        "source_name": "פורום עשה זאת בעצמך",
                        "url": diy_url,
                        "source_label": f"פורום עשה זאת בעצמך — תפוז, פוסט מ-{pub_date_str}",
                        "published_at": pub_date.isoformat() if pub_date else None,
                        "discovered_at": datetime.now(timezone.utc).isoformat()
                    })
    except Exception as exc:
        print(f"[-] DIY forum scrape notice: {exc}")

    print(f"[+] נסרקו בהצלחה {len(leads)} לידים חדשים ממקורות פתוחים")
    return leads


def fetch_gov_tenders(rss_url: str = "https://mr.gov.il/he/Tenders/Pages/SearchTenders.aspx") -> list[dict[str, Any]]:
    """
    סריקת מכרזים ממשלתיים/ציבוריים מתוך פיד RSS או דף מובנה.
    (פונקציית תשתית שניתן לחבר אליה כל פיד RSS של רשות מקומית או מנהל רכש)
    """
    leads = []
    print(f"[*] מתחיל סריקת מכרזים ציבוריים מ: {rss_url}")
    
    try:
        # לדוגמה נשתמש בבקשת GET, במציאות יש להתאים ל-XML/RSS האמיתי
        res = requests.get(rss_url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.content, "xml") # Parsing as XML for RSS
            items = soup.find_all("item")
            
            # אם אין תגיות item (לא RSS קלאסי), ננסה HTML רגיל של טבלאות מכרזים
            if not items:
                soup = BeautifulSoup(res.text, "html.parser")
                # דוגמה לחילוץ שורות מטבלת מכרזים סטנדרטית
                rows = soup.find_all("tr", class_=re.compile("tender|row"))
                for row in rows[:10]:
                    text = row.get_text(separator=" ", strip=True)
                    if any(kw in text for kw in ["בינוי", "שיפוץ", "קבלן", "הקמה", "תשתיות"]):
                        # מציאת הקישור למכרז
                        link_tag = row.find("a")
                        url = link_tag["href"] if link_tag and link_tag.has_attr("href") else rss_url
                        if url.startswith("/"):
                            url = "https://mr.gov.il" + url
                            
                        leads.append({
                            "content": text,
                            "title": "מכרז פומבי: " + text[:50],
                            "source_name": "מנהל הרכש הממשלתי",
                            "url": url,
                            "source_label": f"מנהל הרכש הממשלתי — {datetime.now().strftime('%d/%m/%Y')}",
                            "published_at": datetime.now(timezone.utc).isoformat(),
                            "discovered_at": datetime.now(timezone.utc).isoformat()
                        })
            else:
                for item in items[:15]:
                    title = item.find("title").text if item.find("title") else ""
                    desc = item.find("description").text if item.find("description") else ""
                    pub_date_tag = item.find("pubDate")
                    link = item.find("link").text if item.find("link") else rss_url
                    
                    full_text = f"{title} {desc}"
                    
                    if any(kw in full_text for kw in KEYWORD_SIGNALS + ["בינוי", "תשתיות", "שיפוץ"]):
                        pub_date = None
                        if pub_date_tag:
                            try:
                                # Parsing standard RSS pubDate e.g., 'Mon, 15 Sep 2026 12:00:00 GMT'
                                pub_date = datetime.strptime(pub_date_tag.text, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
                            except ValueError:
                                pass
                                
                        if not is_within_freshness_threshold(pub_date):
                            continue
                            
                        pub_date_str = pub_date.strftime("%d/%m/%Y") if pub_date else datetime.now(timezone.utc).strftime("%d/%m/%Y")
                        
                        leads.append({
                            "content": full_text,
                            "title": title,
                            "source_name": "מכרז ציבורי",
                            "url": link,
                            "source_label": f"מכרז ציבורי (RSS) — {pub_date_str}",
                            "published_at": pub_date.isoformat() if pub_date else None,
                            "discovered_at": datetime.now(timezone.utc).isoformat()
                        })
    except Exception as exc:
        print(f"[-] שגיאה בסריקת מכרזים: {exc}")

    print(f"[+] נסרקו בהצלחה {len(leads)} מכרזים ציבוריים חדשים")
    return leads

