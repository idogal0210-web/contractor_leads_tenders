import os
from datetime import datetime, timezone
from typing import Any, List
try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

def fetch_tavily_leads() -> List[dict[str, Any]]:
    """
    סריקת עומק ברשת לאיתור מכרזים ובקשות שיפוץ ציבוריות מ-24 השעות האחרונות.
    מתבסס על Tavily AI Search API.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or not TavilyClient:
        print("[-] Tavily API key not found. Skipping web intelligence sweep.")
        return []

    client = TavilyClient(api_key=api_key)
    query = "מכרזי שיפוצים ובנייה בישראל בקשות עבודה וקבלנים מהיום"
    
    print(f"[*] מפעיל סוכן מחקר Tavily: '{query}'")
    try:
        response = client.search(
            query=query,
            search_depth="advanced",
            include_raw_content=True,
            max_results=10,
            days=2
        )
    except Exception as e:
        print(f"[-] שגיאה במחקר Tavily: {e}")
        return []

    leads = []
    for result in response.get("results", []):
        url = result.get("url", "")
        title = result.get("title", "")
        content = result.get("raw_content") or result.get("content", "")
        
        # דילוג על אתרי אינדקס זבליים (למרות שTavily לרוב מנקה אותם לבד)
        if "pro.co.il" in url or "shiplus" in url or "d.co.il" in url:
            continue
            
        date_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")
        leads.append({
            "content": content[:3000],  # חותכים כדי לא להעמיס על LLM
            "title": f"Tavily Intel: {title}",
            "source_name": "Tavily Web Intelligence",
            "url": url,
            "source_label": f"מחקר עומק אקטיבי — נסרק ב-{date_str}",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "discovered_at": datetime.now(timezone.utc).isoformat()
        })
        
    print(f"[+] Tavily הביא {len(leads)} לידים לבדיקה")
    return leads
