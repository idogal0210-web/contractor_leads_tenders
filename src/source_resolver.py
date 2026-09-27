import os
import structlog
from tavily import TavilyClient

log = structlog.get_logger(__name__)

def resolve_official_tender_data(tender_title: str, fallback_url: str) -> tuple[str, str]:
    """
    מנסה למצוא את המקור הפתוח והרשמי (למשל באתר המועצה) למכרז שהגיע מלוח סגור.
    מחזיר (URL, raw_content) כך שניתן לשלוח ל-AI את הטקסט המלא מהאתר הרשמי במקום הכותרת היבשה.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return fallback_url, ""
        
    client = TavilyClient(api_key=api_key)
    
    query = f'"{tender_title}" (site:.muni.il OR site:.gov.il)'
    try:
        # First attempt: Exact phrase match on gov/muni sites
        response = client.search(
            query=query,
            search_depth="advanced",
            include_raw_content=True,
            max_results=3,
            exclude_domains=["tenders.co.il", "nevo.co.il", "bdi.co.il", "ifatautotender.co.il", "ifatautotender.com"]
        )
        
        results = response.get("results", [])
        if not results:
            # Second attempt: Without exact quotes but still targeting gov/muni
            response = client.search(
                query=f'{tender_title} מכרז (site:.muni.il OR site:.gov.il)',
                search_depth="advanced",
                include_raw_content=True,
                max_results=3,
                exclude_domains=["tenders.co.il", "nevo.co.il", "bdi.co.il", "ifatautotender.co.il", "ifatautotender.com"]
            )
            results = response.get("results", [])
            
        if not results:
            # Third attempt: Any public site (news, local portals)
            response = client.search(
                query=f'"{tender_title}" מכרז',
                search_depth="advanced",
                include_raw_content=True,
                max_results=3,
                exclude_domains=["tenders.co.il", "nevo.co.il", "bdi.co.il", "ifatautotender.co.il", "ifatautotender.com"]
            )
            results = response.get("results", [])

        # Priority 1: .muni.il or .gov.il
        for res in results:
            url = res.get("url", "")
            if ".muni.il" in url or ".gov.il" in url or "kkl.org.il" in url:
                log.info("Resolved official URL (Priority)", title=tender_title, url=url)
                return url, res.get("raw_content", res.get("content", ""))
                
        # Priority 2: Any other public site that isn't excluded
        if results:
            res = results[0]
            url = res.get("url", "")
            log.info("Resolved public URL (Fallback)", title=tender_title, url=url)
            return url, res.get("raw_content", res.get("content", ""))
            
    except Exception as e:
        log.error("tavily_resolve_error", error=str(e))
        
    return fallback_url, ""
