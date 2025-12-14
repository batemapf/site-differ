"""
Diff snippet generation module.
"""
import difflib
import logging

logger = logging.getLogger(__name__)

# Maximum number of changed lines to include in snippet
MAX_DIFF_LINES = 20
# Maximum line length before truncation
MAX_LINE_LENGTH = 200


def generate_diff_snippet(old_text: str, new_text: str) -> str:
    """
    Generate a human-readable diff snippet between old and new text.
    
    Args:
        old_text: Previous normalized text
        new_text: Current normalized text
    
    Returns:
        Diff snippet as formatted string
    """
    if not old_text:
        # New URL, show first few lines
        lines = new_text.splitlines()[:MAX_DIFF_LINES]
        truncated_lines = [truncate_line(line) for line in lines]
        snippet = '\n'.join(f"+ {line}" for line in truncated_lines)
        if len(new_text.splitlines()) > MAX_DIFF_LINES:
            snippet += f"\n... ({len(new_text.splitlines()) - MAX_DIFF_LINES} more lines)"
        return snippet
    
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    
    # Generate unified diff
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        lineterm='',
        n=0  # No context lines
    )
    
    # Skip the header lines (---, +++, @@)
    diff_lines = list(diff)
    filtered_lines = []
    for line in diff_lines:
        if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
            continue
        filtered_lines.append(line)
    
    # Truncate to MAX_DIFF_LINES
    if len(filtered_lines) > MAX_DIFF_LINES:
        snippet_lines = filtered_lines[:MAX_DIFF_LINES]
        snippet_lines.append(f"... ({len(filtered_lines) - MAX_DIFF_LINES} more changes)")
    else:
        snippet_lines = filtered_lines
    
    # Truncate long lines
    truncated_lines = [truncate_line(line) for line in snippet_lines]
    
    snippet = '\n'.join(truncated_lines)
    
    logger.debug(f"Generated diff snippet: {len(snippet_lines)} lines")
    
    return snippet


def truncate_line(line: str) -> str:
    """
    Truncate a line if it exceeds MAX_LINE_LENGTH.
    
    Args:
        line: Line to truncate
    
    Returns:
        Truncated line with ellipsis if needed
    """
    if len(line) > MAX_LINE_LENGTH:
        return line[:MAX_LINE_LENGTH] + "..."
    return line
