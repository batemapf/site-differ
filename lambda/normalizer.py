"""
HTML normalization and text extraction module.
"""
import hashlib
import re
import logging
from typing import Optional, List
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def normalize_html(html: str, selector: Optional[str] = None,
                   ignore_patterns: Optional[List[str]] = None) -> str:
    """
    Normalize HTML content to extract visible text for comparison.

    Args:
        html: Raw HTML content
        selector: Optional CSS selector to scope extraction
        ignore_patterns: Optional list of regex patterns to remove lines

    Returns:
        Normalized text string
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
    except Exception as e:
        logger.error(f"Failed to parse HTML: {e}")
        raise

    # Remove script, style, and noscript tags
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()

    # Apply selector if provided
    if selector:
        try:
            selected = soup.select(selector)
            if selected:
                # Use only the selected content
                soup = BeautifulSoup('', 'html.parser')
                for elem in selected:
                    soup.append(elem)
                logger.debug(
                    f"Applied selector '{selector}', found {
                        len(selected)} elements")
            else:
                logger.warning(
                    f"Selector '{selector}' matched no elements, "
                    "using full page")
        except Exception as e:
            logger.warning(
                f"Selector '{selector}' failed: {e}, using full page")

    # Extract text
    text = soup.get_text(separator='\n', strip=True)

    # Normalize whitespace
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]  # Remove empty lines

    # Apply ignore patterns
    if ignore_patterns:
        compiled_patterns = []
        for pattern in ignore_patterns:
            try:
                compiled_patterns.append(re.compile(pattern))
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")

        filtered_lines = []
        for line in lines:
            should_ignore = False
            for pattern in compiled_patterns:
                if pattern.search(line):
                    should_ignore = True
                    break
            if not should_ignore:
                filtered_lines.append(line)
        lines = filtered_lines

    # Join lines with single newline
    normalized = '\n'.join(lines)

    logger.debug(
        f"Normalized text length: {
            len(normalized)} chars, {
            len(lines)} lines")

    return normalized


def compute_hash(text: str) -> str:
    """
    Compute SHA-256 hash of text.

    Args:
        text: Text to hash

    Returns:
        Hex-encoded SHA-256 hash
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()
