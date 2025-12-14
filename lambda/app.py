"""
Website Diff Checker Lambda Handler
"""
import json
import os
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone

from fetcher import fetch_url
from normalizer import normalize_html, compute_hash
from diff_generator import generate_diff_snippet
from dynamodb_state import get_state, update_state, touch_state
from ses_notifier import send_digest_email

# Configure logging
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)


def load_urls() -> List[Dict[str, Any]]:
    """
    Load URLs from environment variable URLS_JSON.
    Returns a list of URL objects with optional selectors.
    """
    urls_json = os.environ.get('URLS_JSON', '[]')
    try:
        urls = json.loads(urls_json)
        # Support both simple string list and object list
        result = []
        for url in urls:
            if isinstance(url, str):
                result.append({'url': url, 'selector': None})
            else:
                result.append(url)
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse URLS_JSON: {e}")
        return []


def load_ignore_patterns() -> List[str]:
    """Load regex patterns to ignore from environment variable."""
    ignore_json = os.environ.get('IGNORE_REGEX_JSON', '[]')
    try:
        return json.loads(ignore_json)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse IGNORE_REGEX_JSON: {e}")
        return []


def should_notify(url: str, prev_state: Optional[Dict], cooldown_hours: int) -> bool:
    """
    Determine if we should send a notification for this URL based on cooldown.
    """
    if cooldown_hours <= 0:
        return True
    
    if not prev_state or 'last_notified_at' not in prev_state:
        return True
    
    try:
        last_notified = datetime.fromisoformat(prev_state['last_notified_at'].replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        hours_since = (now - last_notified).total_seconds() / 3600
        return hours_since >= cooldown_hours
    except (ValueError, AttributeError) as e:
        logger.warning(f"Error parsing last_notified_at for {url}: {e}")
        return True


def process_url(url_config: Dict[str, Any], ignore_patterns: List[str], 
                cooldown_hours: int) -> Optional[Dict[str, Any]]:
    """
    Process a single URL: fetch, normalize, hash, compare with state.
    Returns a change record if content changed, None otherwise.
    """
    url = url_config['url']
    selector = url_config.get('selector')
    user_agent = os.environ.get('USER_AGENT', 'Website-Diff-Checker/1.0')
    
    logger.info(f"Processing URL: {url}")
    
    # Get previous state
    prev_state = get_state(url)
    
    # Prepare conditional headers
    conditional_headers = {}
    if prev_state:
        if 'etag' in prev_state and prev_state['etag']:
            conditional_headers['If-None-Match'] = prev_state['etag']
        if 'last_modified' in prev_state and prev_state['last_modified']:
            conditional_headers['If-Modified-Since'] = prev_state['last_modified']
    
    # Fetch URL
    try:
        response = fetch_url(url, user_agent, conditional_headers)
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        # Update error count
        error_count = (prev_state.get('error_count', 0) if prev_state else 0) + 1
        update_state(url, {
            'error_count': error_count,
            'last_error': str(e)[:500],
            'last_checked_at': datetime.now(timezone.utc).isoformat()
        })
        return None
    
    # Handle 304 Not Modified
    if response['status_code'] == 304:
        logger.info(f"URL {url} returned 304 Not Modified")
        touch_state(url)
        return None
    
    # Normalize and hash content
    try:
        normalized_text = normalize_html(response['content'], selector, ignore_patterns)
        new_hash = compute_hash(normalized_text)
    except Exception as e:
        logger.error(f"Failed to normalize content from {url}: {e}")
        error_count = (prev_state.get('error_count', 0) if prev_state else 0) + 1
        update_state(url, {
            'error_count': error_count,
            'last_error': str(e)[:500],
            'last_checked_at': datetime.now(timezone.utc).isoformat()
        })
        return None
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Compare with previous hash
    if prev_state and prev_state.get('last_hash') == new_hash:
        logger.info(f"No change detected for {url}")
        # Reset error count on success
        update_state(url, {
            'last_checked_at': now,
            'error_count': 0
        })
        return None
    
    # Content changed or new URL
    prev_hash = prev_state.get('last_hash') if prev_state else None
    prev_text = prev_state.get('normalized_text') if prev_state else None
    
    logger.info(f"Change detected for {url} (new hash: {new_hash})")
    
    # Update state
    state_update = {
        'last_hash': new_hash,
        'last_checked_at': now,
        'last_changed_at': now,
        'error_count': 0,
        'normalized_text': normalized_text  # Store for next diff
    }
    
    # Store response headers for conditional requests
    if 'etag' in response:
        state_update['etag'] = response['etag']
    if 'last_modified' in response:
        state_update['last_modified'] = response['last_modified']
    
    # Check if we should notify
    change_record = None
    if should_notify(url, prev_state, cooldown_hours):
        state_update['last_notified_at'] = now
        
        # Generate diff snippet
        diff_snippet = generate_diff_snippet(prev_text or "", normalized_text)
        
        change_record = {
            'url': url,
            'previous_hash': prev_hash,
            'new_hash': new_hash,
            'diff_snippet': diff_snippet,
            'is_new': prev_hash is None
        }
    else:
        logger.info(f"Skipping notification for {url} due to cooldown")
    
    # Always update state when content changes, regardless of notification
    update_state(url, state_update)
    return change_record


def lambda_handler(event, context):
    """
    Main Lambda handler function.
    """
    logger.info("Starting Website Diff Checker Lambda")
    logger.debug(f"Event: {json.dumps(event)}")
    
    # Load configuration
    url_configs = load_urls()
    ignore_patterns = load_ignore_patterns()
    cooldown_hours = int(os.environ.get('COOLDOWN_HOURS', '0'))
    
    if not url_configs:
        logger.warning("No URLs configured")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'No URLs to check'})
        }
    
    logger.info(f"Checking {len(url_configs)} URLs")
    
    # Process all URLs
    changes = []
    for url_config in url_configs:
        change = process_url(url_config, ignore_patterns, cooldown_hours)
        if change:
            changes.append(change)
    
    # Send digest email if there are changes
    if changes:
        logger.info(f"Detected {len(changes)} changed URLs")
        try:
            send_digest_email(changes, len(url_configs))
            logger.info("Digest email sent successfully")
        except Exception as e:
            logger.error(f"Failed to send digest email: {e}")
            # Don't fail the whole run if email fails
    else:
        logger.info("No changes detected")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Website diff check completed',
            'urls_checked': len(url_configs),
            'changes_detected': len(changes)
        })
    }
