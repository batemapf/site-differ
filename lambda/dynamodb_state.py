"""
DynamoDB state management module.
"""
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Lazy initialization
_dynamodb = None
_table = None


def _get_table():
    """Get or create DynamoDB table resource."""
    global _dynamodb, _table
    if _table is None:
        _dynamodb = boto3.resource('dynamodb')
        table_name = os.environ.get('DDB_TABLE', 'website_diff_state')
        _table = _dynamodb.Table(table_name)
    return _table


def get_state(url: str) -> Optional[Dict[str, Any]]:
    """
    Get the current state for a URL from DynamoDB.

    Args:
        url: The URL to look up

    Returns:
        Dict with state data or None if not found
    """
    try:
        table = _get_table()
        response = table.get_item(Key={'url': url})
        item = response.get('Item')
        if item:
            logger.debug(
                f"Found state for {url}: hash={
                    item.get(
                        'last_hash',
                        'N/A')}")
        return item
    except ClientError as e:
        logger.error(f"DynamoDB get_item failed for {url}: {e}")
        return None


def update_state(url: str, updates: Dict[str, Any]) -> None:
    """
    Update state for a URL in DynamoDB.

    Args:
        url: The URL to update
        updates: Dict of attributes to update
    """
    try:
        table = _get_table()
        # Build update expression
        update_expr_parts = []
        expr_attr_values = {}

        for key, value in updates.items():
            update_expr_parts.append(f"{key} = :{key}")
            expr_attr_values[f":{key}"] = value

        update_expr = "SET " + ", ".join(update_expr_parts)

        table.update_item(
            Key={'url': url},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_attr_values
        )

        logger.debug(f"Updated state for {url}: {updates}")

    except ClientError as e:
        logger.error(f"DynamoDB update_item failed for {url}: {e}")
        raise


def touch_state(url: str) -> None:
    """
    Update only the last_checked_at timestamp for a URL.

    Args:
        url: The URL to touch
    """
    now = datetime.now(timezone.utc).isoformat()
    update_state(url, {'last_checked_at': now})
