import concurrent.futures
from typing import Tuple, List, Optional
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup

from core.db.models import Opportunity, UrlValidationStatus

def validate_source_url(url: str) -> Tuple[UrlValidationStatus, Optional[str]]:
    """
    Validates a URL by making a GET request.
    Returns the status and the final resolved URL.
    """
    if not url:
        return UrlValidationStatus.INVALID, None

    try:
        response = requests.get(url, timeout=5, allow_redirects=True)
        final_url = response.url

        if response.status_code >= 400:
            return UrlValidationStatus.INVALID, final_url

        # Check for login pages (simple heuristic)
        # Often forums or portals requiring authentication return 200 with a login form
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' in content_type:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Look for password input fields
            password_inputs = soup.find_all('input', {'type': 'password'})
            if password_inputs:
                return UrlValidationStatus.REQUIRES_AUTH, final_url

        return UrlValidationStatus.VALID, final_url

    except requests.RequestException:
        return UrlValidationStatus.INVALID, url
    except Exception:
        return UrlValidationStatus.INVALID, url

def should_validate(opportunity: Opportunity, ttl_hours: int = 24) -> bool:
    """
    Checks if an opportunity's URL needs validation based on TTL.
    """
    # If it has no URL via source_item, no need to validate
    if not hasattr(opportunity, "source_item") or not opportunity.source_item or not opportunity.source_item.url:
        return False

    if not opportunity.last_validated_at:
        return True
    
    # Ensure last_validated_at is timezone-aware before comparison
    last_val = opportunity.last_validated_at
    if last_val.tzinfo is None:
        last_val = last_val.replace(tzinfo=timezone.utc)
        
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl_hours)
    return last_val < cutoff

def validate_opportunities_batch(opportunities: List[Opportunity], max_workers: int = 5) -> None:
    """
    Validates a batch of opportunities in parallel and updates their fields in-place.
    """
    opportunities_to_validate = [opp for opp in opportunities if should_validate(opp)]
    
    if not opportunities_to_validate:
        return

    def validate_opp(opp: Opportunity):
        url = opp.source_item.url
        status, final_url = validate_source_url(url)
        
        opp.validation_status = status
        # Update source_item URL if redirected
        if final_url and final_url != opp.source_item.url:
            opp.source_item.url = final_url
        
        opp.last_validated_at = datetime.now(timezone.utc)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(validate_opp, opportunities_to_validate))
