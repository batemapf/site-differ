"""
Unit tests for HTML normalization and hashing.
"""
from normalizer import normalize_html, compute_hash
import unittest
import sys
import os

# Add lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))


class TestNormalizer(unittest.TestCase):

    def test_basic_html_normalization(self):
        """Test basic HTML text extraction."""
        html = """
        <html>
            <head><title>Test</title></head>
            <body>
                <h1>Hello World</h1>
                <p>This is a test.</p>
            </body>
        </html>
        """
        normalized = normalize_html(html)
        self.assertIn("Hello World", normalized)
        self.assertIn("This is a test.", normalized)
        self.assertNotIn("<h1>", normalized)
        self.assertNotIn("</p>", normalized)

    def test_script_and_style_removal(self):
        """Test that script and style tags are removed."""
        html = """
        <html>
            <head>
                <style>body { color: red; }</style>
                <script>alert('test');</script>
            </head>
            <body>
                <p>Visible content</p>
                <script>console.log('hidden');</script>
            </body>
        </html>
        """
        normalized = normalize_html(html)
        self.assertIn("Visible content", normalized)
        self.assertNotIn("color: red", normalized)
        self.assertNotIn("alert", normalized)
        self.assertNotIn("console.log", normalized)

    def test_whitespace_normalization(self):
        """Test that whitespace is normalized."""
        html = """
        <html>
            <body>
                <p>Line   with    spaces</p>
                <p>Multiple


                newlines</p>
            </body>
        </html>
        """
        normalized = normalize_html(html)
        lines = normalized.splitlines()
        # Each line should be trimmed
        for line in lines:
            self.assertEqual(line, line.strip())
        # No empty lines
        self.assertNotIn("", lines)

    def test_css_selector(self):
        """Test CSS selector scoping."""
        html = """
        <html>
            <body>
                <header>Header content</header>
                <main id="content">
                    <p>Main content</p>
                </main>
                <footer>Footer content</footer>
            </body>
        </html>
        """
        normalized = normalize_html(html, selector="#content")
        self.assertIn("Main content", normalized)
        self.assertNotIn("Header content", normalized)
        self.assertNotIn("Footer content", normalized)

    def test_invalid_selector_fallback(self):
        """Test that invalid selector falls back to full page."""
        html = "<html><body><p>Test content</p></body></html>"
        normalized = normalize_html(html, selector="#nonexistent")
        self.assertIn("Test content", normalized)

    def test_ignore_patterns(self):
        """Test regex pattern filtering."""
        html = """
        <html>
            <body>
                <p>Keep this line</p>
                <p>Last updated: 2024-01-01</p>
                <p>Also keep this</p>
            </body>
        </html>
        """
        ignore_patterns = [r"Last updated:.*"]
        normalized = normalize_html(html, ignore_patterns=ignore_patterns)
        self.assertIn("Keep this line", normalized)
        self.assertIn("Also keep this", normalized)
        self.assertNotIn("Last updated", normalized)

    def test_compute_hash_consistency(self):
        """Test that hash computation is consistent."""
        text = "This is a test string."
        hash1 = compute_hash(text)
        hash2 = compute_hash(text)
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)  # SHA-256 produces 64 hex chars

    def test_compute_hash_difference(self):
        """Test that different text produces different hashes."""
        hash1 = compute_hash("Text A")
        hash2 = compute_hash("Text B")
        self.assertNotEqual(hash1, hash2)

    def test_empty_html(self):
        """Test handling of empty HTML."""
        normalized = normalize_html("")
        self.assertEqual(normalized, "")

    def test_noscript_removal(self):
        """Test that noscript tags are removed."""
        html = """
        <html>
            <body>
                <p>Normal content</p>
                <noscript>JavaScript is disabled</noscript>
            </body>
        </html>
        """
        normalized = normalize_html(html)
        self.assertIn("Normal content", normalized)
        self.assertNotIn("JavaScript is disabled", normalized)


if __name__ == '__main__':
    unittest.main()
