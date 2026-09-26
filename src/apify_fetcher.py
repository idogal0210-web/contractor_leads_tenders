import os
from apify_client import ApifyClient
from typing import List, Dict, Any
import structlog
from datetime import datetime, timezone

log = structlog.get_logger(__name__)

def fetch_facebook_leads_from_apify() -> List[Dict[str, Any]]:
    token = os.getenv("APIFY_API_TOKEN")
    task_id = os.getenv("APIFY_FACEBOOK_TASK_ID")
    
    if not token or not task_id:
        log.warning("apify_credentials_missing", reason="APIFY_API_TOKEN or APIFY_FACEBOOK_TASK_ID not found in environment.")
        return []
        
    client = ApifyClient(token)
    leads = []
    
    try:
        log.info("Starting Apify extraction for Facebook B2C leads...", task_id=task_id)
        
        # שליפת הריצה האחרונה שהסתיימה בהצלחה
        runs = client.task(task_id).runs().list(desc=True, limit=1)
        if not runs.items:
            log.info("No successful runs found for Apify task.", task_id=task_id)
            return []
            
        last_run = runs.items[0]
        dataset_id = last_run["defaultDatasetId"]
        
        # שאיבת כל הפוסטים מהדאטה-סט
        dataset_items = client.dataset(dataset_id).list_items().items
        
        for item in dataset_items:
            # Structuring depends on the specific Apify Actor used, but generally looks for 'text' or 'message'
            text = item.get("text") or item.get("message")
            if not text:
                continue
                
            user_info = item.get("user", {})
            user_name = user_info.get("name") if isinstance(user_info, dict) else "אנונימי"
            
            leads.append({
                "content": text,
                "title": f"פוסט פייסבוק מ: {user_name}",
                "source_name": "Facebook Groups via Apify",
                "url": item.get("url", item.get("postUrl", "")),
                "source_label": "מקור אמת - B2C",
                "published_at": item.get("date") or item.get("time") or datetime.now(timezone.utc).isoformat(),
                "discovered_at": datetime.now(timezone.utc).isoformat()
            })
            
        log.info(f"Pulled {len(leads)} raw Facebook posts from Apify.")
        return leads
    except Exception as e:
        log.error("apify_fetch_error", error=str(e))
        return []

