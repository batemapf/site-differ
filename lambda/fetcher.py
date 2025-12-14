"""
URL fetcher module with conditional request support.
"""
import logging
import requests
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Default timeouts
CONNECT_TIMEOUT = 3
READ_TIMEOUT = 10


def fetch_url(url: str, user_agent: str, 
              conditional_headers: Optional[Dict[str, str]] = None) -> Dict:
    """
    Fetch a URL with conditional headers support.
    
    Args:
        url: The URL to fetch
        user_agent: User-Agent string to use
        conditional_headers: Optional dict with If-None-Match, If-Modified-Since headers
    
    Returns:
        Dict with status_code, content, etag, last_modified
    
    Raises:
        Exception: On fetch failure
    """
    headers = {
        'User-Agent': user_agent
    }
    
    if conditional_headers:
        headers.update(conditional_headers)
    
    logger.debug(f"Fetching {url} with headers: {headers}")
    
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            allow_redirects=True
        )
        
        # Don't raise on 304, we handle it specially
        if response.status_code != 304:
            response.raise_for_status()
        
        result = {
            'status_code': response.status_code,
            'content': response.text if response.status_code != 304 else None
        }
        
        # Extract caching headers
        if 'ETag' in response.headers:
            result['etag'] = response.headers['ETag']
        if 'Last-Modified' in response.headers:
            result['last_modified'] = response.headers['Last-Modified']
        
        logger.info(f"Fetched {url}: status={response.status_code}, "
                   f"length={len(response.text) if response.text else 0}")
        
        return result
        
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout fetching {url}: {e}")
        raise Exception(f"Timeout: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {url}: {e}")
        raise Exception(f"Request failed: {e}")
