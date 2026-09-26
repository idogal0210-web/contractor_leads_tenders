import os
import structlog
from tavily import TavilyClient

log = structlog.get_logger(__name__)

def resolve_official_tender_url(tender_title: str, fallback_url: str) -> str:
    """
    מנסה למצוא את המקור הפתוח והרשמי (למשל באתר המועצה) למכרז שהגיע מלוח סגור.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return fallback_url
        
    client = TavilyClient(api_key=api_key)
    
    # We want to find the exact tender, prioritizing municipal/government sites
    query = f'"{tender_title}" מכרז'
    try:
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=5,
            include_domains=[], # We could restrict, but better to filter post-search
            exclude_domains=["tenders.co.il", "nevo.co.il", "bdi.co.il", "ifatautotender.co.il"]
        )
        
        results = response.get("results", [])
        if not results:
            # Try a broader search without quotes
            response = client.search(
                query=f"{tender_title} מכרז",
                search_depth="basic",
                max_results=5,
                exclude_domains=["tenders.co.il", "nevo.co.il", "bdi.co.il", "ifatautotender.co.il"]
            )
            results = response.get("results", [])

        # Priority 1: .muni.il or .gov.il
        for res in results:
            url = res.get("url", "")
            if ".muni.il" in url or ".gov.il" in url or "kkl.org.il" in url:
                log.info("Resolved official URL (Priority)", title=tender_title, url=url)
                return url
                
        # Priority 2: Any other public site that isn't excluded
        if results:
            url = results[0].get("url", "")
            log.info("Resolved public URL (Fallback)", title=tender_title, url=url)
            return url
            
    except Exception as e:
        log.error("tavily_resolve_error", error=str(e))
        
    return fallback_url

