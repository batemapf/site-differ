"""
Unit tests for Lambda handler logic.
"""
import unittest
import sys
import os
from unittest.mock import patch

# Add lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

# Mock AWS services before importing modules that use them
with patch('boto3.resource'), patch('boto3.client'):
    from app import load_urls, load_ignore_patterns, should_notify, process_url


class TestLambdaHandler(unittest.TestCase):
    
    @patch.dict(os.environ, {'URLS_JSON': '["https://example.com", "https://test.com"]'})
    def test_load_urls_simple_list(self):
        """Test loading URLs from simple string list."""
        urls = load_urls()
        self.assertEqual(len(urls), 2)
        self.assertEqual(urls[0]['url'], "https://example.com")
        self.assertEqual(urls[0]['selector'], None)
    
    @patch.dict(os.environ, {'URLS_JSON': '[{"url": "https://example.com", "selector": "#main"}]'})
    def test_load_urls_with_selector(self):
        """Test loading URLs with selectors."""
        urls = load_urls()
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0]['url'], "https://example.com")
        self.assertEqual(urls[0]['selector'], "#main")
    
    @patch.dict(os.environ, {'URLS_JSON': 'invalid json'})
    def test_load_urls_invalid_json(self):
        """Test handling of invalid JSON."""
        urls = load_urls()
        self.assertEqual(urls, [])
    
    @patch.dict(os.environ, {'IGNORE_REGEX_JSON': '["pattern1", "pattern2"]'})
    def test_load_ignore_patterns(self):
        """Test loading ignore patterns."""
        patterns = load_ignore_patterns()
        self.assertEqual(len(patterns), 2)
        self.assertEqual(patterns[0], "pattern1")
    
    def test_should_notify_no_cooldown(self):
        """Test notification when cooldown is 0."""
        result = should_notify("https://example.com", None, 0)
        self.assertTrue(result)
    
    def test_should_notify_no_previous_state(self):
        """Test notification when there's no previous state."""
        result = should_notify("https://example.com", None, 6)
        self.assertTrue(result)
    
    def test_should_notify_within_cooldown(self):
        """Test notification is blocked within cooldown period."""
        from datetime import datetime, timezone, timedelta
        
        # Last notified 1 hour ago
        last_notified = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        prev_state = {'last_notified_at': last_notified}
        
        # Cooldown is 6 hours
        result = should_notify("https://example.com", prev_state, 6)
        self.assertFalse(result)
    
    def test_should_notify_after_cooldown(self):
        """Test notification is allowed after cooldown period."""
        from datetime import datetime, timezone, timedelta
        
        # Last notified 7 hours ago
        last_notified = (datetime.now(timezone.utc) - timedelta(hours=7)).isoformat()
        prev_state = {'last_notified_at': last_notified}
        
        # Cooldown is 6 hours
        result = should_notify("https://example.com", prev_state, 6)
        self.assertTrue(result)
    
    @patch('app.touch_state')
    @patch('app.get_state')
    @patch('app.fetch_url')
    @patch.dict(os.environ, {'USER_AGENT': 'Test/1.0'})
    def test_process_url_304_response(self, mock_fetch, mock_get_state, mock_touch):
        """Test processing URL that returns 304 Not Modified."""
        mock_get_state.return_value = {
            'last_hash': 'oldhash',
            'etag': 'etag123'
        }
        mock_fetch.return_value = {'status_code': 304}
        
        url_config = {'url': 'https://example.com', 'selector': None}
        result = process_url(url_config, [], 0)
        
        self.assertIsNone(result)
        # Should call touch_state
        self.assertTrue(mock_touch.called)
    
    @patch('app.get_state')
    @patch('app.fetch_url')
    @patch('app.update_state')
    @patch.dict(os.environ, {'USER_AGENT': 'Test/1.0'})
    def test_process_url_fetch_error(self, mock_update, mock_fetch, mock_get_state):
        """Test processing URL that fails to fetch."""
        mock_get_state.return_value = None
        mock_fetch.side_effect = Exception("Network error")
        
        url_config = {'url': 'https://example.com', 'selector': None}
        result = process_url(url_config, [], 0)
        
        self.assertIsNone(result)
        # Should update error count
        self.assertTrue(mock_update.called)
        call_args = mock_update.call_args[0]
        self.assertIn('error_count', call_args[1])


if __name__ == '__main__':
    unittest.main()
