import os
from datetime import datetime, timezone
from typing import List, Dict, Any
from apify_client import ApifyClient
import structlog

log = structlog.get_logger(__name__)

def fetch_facebook_leads_from_apify() -> List[Dict[str, Any]]:
    """
    מפעיל את האקטור apify/facebook-groups-scraper בכדי לאסוף לידים
    מקבוצות פייסבוק רלוונטיות (שיפוצים, קבלני שיפוצים, בונים ומשפצים).
    """
    token = os.getenv("APIFY_API_TOKEN")
    
    if not token:
        log.warning("apify_credentials_missing", reason="APIFY_API_TOKEN not found in environment.")
        return []
        
    client = ApifyClient(token)
    leads = []
    
    # הגדרת הקלט לאקטור. נניח כתובות של קבוצות פייסבוק בתחום:
    run_input = {
        "startUrls": [
            {"url": "https://www.facebook.com/groups/Ask.shipuznik/"},      # תשאל שיפוצניק
            {"url": "https://www.facebook.com/groups/1012921078732649/"},   # קבלנים רשומים וממליצים
            {"url": "https://www.facebook.com/groups/439773216503926/"}     # עבודות שיפוצים הוגנים
        ],
        "resultsLimit": 15,
        "maxPosts": 15,
        "proxyConfiguration": {
            "useApifyProxy": True
        }
    }
    
    try:
        log.info("Starting Apify actor for Facebook B2C leads...", actor="apify/facebook-groups-scraper")
        
        # הרצת האקטור והמתנה לסיום
        run = client.actor("apify/facebook-groups-scraper").call(run_input=run_input)
        
        if not run:
            log.warning("apify_run_failed", reason="No run returned from Apify.")
            return []
            
        dataset_id = run.get("defaultDatasetId")
        if not dataset_id:
            log.warning("apify_no_dataset", reason="No dataset ID returned from run.")
            return []
            
        log.info("Apify actor finished successfully. Fetching dataset items...", dataset_id=dataset_id)
        
        # שאיבת כל הפוסטים מהדאטה-סט
        dataset_items = client.dataset(dataset_id).iterate_items()
        
        for item in dataset_items:
            # המבנה תלוי בפלט הספציפי של האקטור
            text = item.get("text") or item.get("message")
            if not text:
                continue
                
            post_url = item.get("url") or item.get("postUrl") or ""
            date = item.get("date") or item.get("time") or datetime.now(timezone.utc).isoformat()
            
            leads.append({
                "content": text,
                "title": "פוסט מפייסבוק",
                "source_name": "קבוצות פייסבוק",
                "url": post_url,
                "source_label": "B2C / רשתות חברתיות",
                "published_at": date,
                "discovered_at": datetime.now(timezone.utc).isoformat()
            })
            
        log.info(f"Pulled {len(leads)} raw Facebook posts from Apify.")
        return leads
        
    except Exception as e:
        log.error("apify_fetch_error", error=str(e))
        return []
