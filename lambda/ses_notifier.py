"""
SES email notification module.
"""
import os
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Lazy initialization
_ses = None


def _get_ses_client():
    """Get or create SES client."""
    global _ses
    if _ses is None:
        _ses = boto3.client('ses')
    return _ses


def send_digest_email(changes: List[Dict[str, Any]], total_urls: int) -> None:
    """
    Send a digest email with all detected changes.
    
    Args:
        changes: List of change records
        total_urls: Total number of URLs checked
    """
    from_address = os.environ.get('SES_FROM')
    to_addresses_str = os.environ.get('SES_TO', '')
    to_addresses = [addr.strip() for addr in to_addresses_str.split(',') if addr.strip()]
    
    if not from_address or not to_addresses:
        raise ValueError("SES_FROM and SES_TO environment variables must be set")
    
    # Generate email subject
    now = datetime.now(timezone.utc)
    subject = f"Website changes detected ({len(changes)} of {total_urls}) - {now.strftime('%Y-%m-%d %H:%M UTC')}"
    
    # Generate email body
    body_text = generate_text_body(changes, total_urls, now)
    body_html = generate_html_body(changes, total_urls, now)
    
    try:
        ses = _get_ses_client()
        response = ses.send_email(
            Source=from_address,
            Destination={
                'ToAddresses': to_addresses
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': body_text,
                        'Charset': 'UTF-8'
                    },
                    'Html': {
                        'Data': body_html,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        logger.info(f"Email sent successfully: MessageId={response['MessageId']}")
    except ClientError as e:
        logger.error(f"Failed to send email via SES: {e}")
        raise


def generate_text_body(changes: List[Dict[str, Any]], total_urls: int, 
                       run_time: datetime) -> str:
    """
    Generate plain text email body.
    
    Args:
        changes: List of change records
        total_urls: Total number of URLs checked
        run_time: Time of this run
    
    Returns:
        Plain text email body
    """
    lines = [
        "Website Diff Checker - Change Report",
        "=" * 60,
        f"Run time: {run_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"URLs checked: {total_urls}",
        f"Changes detected: {len(changes)}",
        "",
    ]
    
    for i, change in enumerate(changes, 1):
        lines.append(f"{i}. {change['url']}")
        if change['is_new']:
            lines.append("   Status: NEW URL")
        else:
            lines.append(f"   Previous hash: {change['previous_hash'][:16]}...")
            lines.append(f"   New hash:      {change['new_hash'][:16]}...")
        lines.append("")
        lines.append("   Changes:")
        lines.append("   " + "-" * 56)
        for diff_line in change['diff_snippet'].splitlines():
            lines.append("   " + diff_line)
        lines.append("   " + "-" * 56)
        lines.append("")
    
    lines.append("=" * 60)
    lines.append("This is an automated message from Website Diff Checker.")
    
    return '\n'.join(lines)


def generate_html_body(changes: List[Dict[str, Any]], total_urls: int, 
                       run_time: datetime) -> str:
    """
    Generate HTML email body.
    
    Args:
        changes: List of change records
        total_urls: Total number of URLs checked
        run_time: Time of this run
    
    Returns:
        HTML email body
    """
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<style>",
        "body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }",
        "h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }",
        ".summary { background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }",
        ".change { border: 1px solid #bdc3c7; border-radius: 5px; padding: 15px; margin: 20px 0; }",
        ".change-header { font-weight: bold; color: #2980b9; margin-bottom: 10px; }",
        ".url { color: #3498db; word-break: break-all; }",
        ".status { color: #27ae60; font-weight: bold; }",
        ".diff { background: #f8f9fa; padding: 10px; border-left: 4px solid #3498db; font-family: monospace; white-space: pre-wrap; overflow-x: auto; }",
        ".added { color: #27ae60; }",
        ".removed { color: #e74c3c; }",
        ".footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #bdc3c7; font-size: 0.9em; color: #7f8c8d; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Website Diff Checker - Change Report</h1>",
        "<div class='summary'>",
        f"<p><strong>Run time:</strong> {run_time.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>",
        f"<p><strong>URLs checked:</strong> {total_urls}</p>",
        f"<p><strong>Changes detected:</strong> {len(changes)}</p>",
        "</div>",
    ]
    
    for i, change in enumerate(changes, 1):
        html_parts.append(f"<div class='change'>")
        html_parts.append(f"<div class='change-header'>{i}. Change Detected</div>")
        html_parts.append(f"<p><strong>URL:</strong> <a href='{escape_html(change['url'])}' class='url'>{escape_html(change['url'])}</a></p>")
        
        if change['is_new']:
            html_parts.append("<p class='status'>Status: NEW URL</p>")
        else:
            html_parts.append(f"<p><strong>Previous hash:</strong> <code>{change['previous_hash'][:16]}...</code></p>")
            html_parts.append(f"<p><strong>New hash:</strong> <code>{change['new_hash'][:16]}...</code></p>")
        
        html_parts.append("<p><strong>Changes:</strong></p>")
        html_parts.append("<div class='diff'>")
        
        # Format diff with colors
        for line in change['diff_snippet'].splitlines():
            if line.startswith('+'):
                html_parts.append(f"<span class='added'>{escape_html(line)}</span>")
            elif line.startswith('-'):
                html_parts.append(f"<span class='removed'>{escape_html(line)}</span>")
            else:
                html_parts.append(escape_html(line))
        
        html_parts.append("</div>")
        html_parts.append("</div>")
    
    html_parts.append("<div class='footer'>")
    html_parts.append("<p>This is an automated message from Website Diff Checker.</p>")
    html_parts.append("</div>")
    html_parts.append("</body>")
    html_parts.append("</html>")
    
    return '\n'.join(html_parts)


def escape_html(text: str) -> str:
    """
    Escape HTML special characters.
    
    Args:
        text: Text to escape
    
    Returns:
        Escaped text
    """
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))
