import httpx
from datetime import datetime, timezone
import structlog
from typing import List, Dict, Any

log = structlog.get_logger(__name__)

def fetch_live_web_leads() -> List[Dict[str, Any]]:
    return []

def fetch_gov_tenders() -> List[Dict[str, Any]]:
    """
    1. אינטגרציה ישירה ופולרית (M2M / API) - למכרזים מוסדיים
    """
    leads = []
    log.info("Starting B2G Direct API Polling (M2M)...")
    
    # ה-API של מנהל הרכש / Data.gov.il למכרזים
    url = "https://data.gov.il/api/3/action/datastore_search"
    params = {
        "resource_id": "7038b3e6-a74d-442e-b16b-466c8196124a",
        "limit": 50,
        "sort": "_id desc"
    }
    
    try:
        response = httpx.get(url, params=params, timeout=15.0)
        response.raise_for_status()
        data = response.json()
        
        records = data.get("result", {}).get("records", [])
        
        # נסנן מכרזים שרלוונטיים לעבודות קבלניות / בינוי
        relevant_keywords = ["בינוי", "שיפוץ", "קבלן", "תשתיות", "חשמל", "מבנה", "מבנים"]
        
        for record in records:
            title = record.get("שם הליך", "")
            publisher = record.get("שם יחידה מפרסמת", "")
            tender_id = record.get("מספר הליך", "")
            status = record.get("סטטוס", "")
            published_date = record.get("תאריך פרסום", "")
            
            # אם אין כותרת, או שהמכרז מוגדר סגור, נדלג (בטסט נשאיר גם סגורים רק כדי להדגים)
            if not title:
                continue
                
            if not any(k in title or k in record.get("נושאים", "") for k in relevant_keywords):
                continue
                
            content = (
                f"מכרז ממשלתי רשמי: {title}\n"
                f"מפרסם: {publisher}\n"
                f"מספר הליך: {tender_id}\n"
                f"סטטוס במערכת: {status}\n"
                f"תאריך עדכון/פרסום: {published_date}"
            )
            
            leads.append({
                "content": content,
                "title": title,
                "source_name": f"Gov.il API - {publisher}",
                "url": f"https://mr.gov.il/Tender/{tender_id}",
                "source_label": "אינטגרציית M2M ישירה (מכרז ציבורי)",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "discovered_at": datetime.now(timezone.utc).isoformat()
            })
            
            if len(leads) >= 10:
                break
                
        log.info(f"Pulled {len(leads)} verified B2G tenders via API.")
        return leads

    except Exception as e:
        log.error("b2g_api_polling_error", error=str(e))
        return []
