"""
Unit tests for diff snippet generation.
"""
import unittest
import sys
import os

# Add lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from diff_generator import generate_diff_snippet, truncate_line


class TestDiffGenerator(unittest.TestCase):
    
    def test_new_content_snippet(self):
        """Test diff snippet for new content (no previous text)."""
        new_text = "Line 1\nLine 2\nLine 3"
        snippet = generate_diff_snippet("", new_text)
        self.assertIn("+ Line 1", snippet)
        self.assertIn("+ Line 2", snippet)
        self.assertIn("+ Line 3", snippet)
    
    def test_simple_change(self):
        """Test diff snippet for simple text change."""
        old_text = "Line 1\nLine 2\nLine 3"
        new_text = "Line 1\nLine 2 modified\nLine 3"
        snippet = generate_diff_snippet(old_text, new_text)
        # Should show the removed and added lines
        self.assertIn("Line 2", snippet)
    
    def test_added_lines(self):
        """Test diff snippet for added lines."""
        old_text = "Line 1\nLine 2"
        new_text = "Line 1\nLine 2\nLine 3"
        snippet = generate_diff_snippet(old_text, new_text)
        self.assertIn("+", snippet)
        self.assertIn("Line 3", snippet)
    
    def test_removed_lines(self):
        """Test diff snippet for removed lines."""
        old_text = "Line 1\nLine 2\nLine 3"
        new_text = "Line 1\nLine 3"
        snippet = generate_diff_snippet(old_text, new_text)
        self.assertIn("-", snippet)
        self.assertIn("Line 2", snippet)
    
    def test_max_diff_lines_truncation(self):
        """Test that diff is truncated to MAX_DIFF_LINES."""
        old_lines = [f"Old line {i}" for i in range(50)]
        new_lines = [f"New line {i}" for i in range(50)]
        old_text = '\n'.join(old_lines)
        new_text = '\n'.join(new_lines)
        
        snippet = generate_diff_snippet(old_text, new_text)
        snippet_lines = snippet.splitlines()
        
        # Should be truncated with a message about more changes
        self.assertIn("more changes", snippet.lower())
    
    def test_truncate_line_short(self):
        """Test that short lines are not truncated."""
        line = "Short line"
        result = truncate_line(line)
        self.assertEqual(line, result)
    
    def test_truncate_line_long(self):
        """Test that long lines are truncated."""
        line = "x" * 300
        result = truncate_line(line)
        self.assertTrue(len(result) < len(line))
        self.assertTrue(result.endswith("..."))
    
    def test_no_change(self):
        """Test diff when there's no change."""
        text = "Line 1\nLine 2\nLine 3"
        snippet = generate_diff_snippet(text, text)
        # Should produce minimal or empty output
        self.assertIsInstance(snippet, str)
    
    def test_empty_old_text_many_lines(self):
        """Test new content with many lines is truncated."""
        new_lines = [f"Line {i}" for i in range(100)]
        new_text = '\n'.join(new_lines)
        snippet = generate_diff_snippet("", new_text)
        snippet_lines = snippet.splitlines()
        
        # Should mention more lines
        self.assertIn("more lines", snippet.lower())


if __name__ == '__main__':
    unittest.main()
