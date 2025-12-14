"""
Integration tests for the Lambda handler.
"""
import unittest
import sys
import os
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

# Add lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

# Mock AWS services before importing
with patch('boto3.resource'), patch('boto3.client'):
    from app import lambda_handler


class TestLambdaHandlerIntegration(unittest.TestCase):
    """Integration tests for the complete Lambda handler."""
    
    @patch.dict(os.environ, {
        'URLS_JSON': '["https://example.com"]',
        'DDB_TABLE': 'test-table',
        'SES_FROM': 'noreply@test.com',
        'SES_TO': 'user@test.com',
        'USER_AGENT': 'Test/1.0',
        'LOG_LEVEL': 'INFO'
    })
    @patch('app.send_digest_email')
    @patch('app.update_state')
    @patch('app.get_state')
    @patch('app.fetch_url')
    @patch('app.normalize_html')
    @patch('app.compute_hash')
    def test_new_url_triggers_notification(self, mock_hash, mock_normalize, mock_fetch,
                                          mock_get_state, mock_update, mock_send_email):
        """Test that a new URL triggers a notification."""
        # Setup mocks
        mock_get_state.return_value = None  # New URL
        mock_fetch.return_value = {
            'status_code': 200,
            'content': '<html><body>Test content</body></html>',
            'etag': 'abc123'
        }
        mock_normalize.return_value = "Test content"
        mock_hash.return_value = "newhash123"
        
        # Execute
        result = lambda_handler({}, {})
        
        # Verify
        self.assertEqual(result['statusCode'], 200)
        body = json.loads(result['body'])
        self.assertEqual(body['urls_checked'], 1)
        self.assertEqual(body['changes_detected'], 1)
        
        # Verify email was sent
        self.assertTrue(mock_send_email.called)
        changes = mock_send_email.call_args[0][0]
        self.assertEqual(len(changes), 1)
        self.assertTrue(changes[0]['is_new'])
    
    @patch.dict(os.environ, {
        'URLS_JSON': '["https://example.com"]',
        'DDB_TABLE': 'test-table',
        'SES_FROM': 'noreply@test.com',
        'SES_TO': 'user@test.com',
        'USER_AGENT': 'Test/1.0',
        'LOG_LEVEL': 'INFO'
    })
    @patch('app.send_digest_email')
    @patch('app.update_state')
    @patch('app.get_state')
    @patch('app.fetch_url')
    @patch('app.normalize_html')
    @patch('app.compute_hash')
    def test_unchanged_url_no_notification(self, mock_hash, mock_normalize, mock_fetch,
                                          mock_get_state, mock_update, mock_send_email):
        """Test that an unchanged URL doesn't trigger notification."""
        # Setup mocks
        mock_get_state.return_value = {'last_hash': 'samehash123'}
        mock_fetch.return_value = {
            'status_code': 200,
            'content': '<html><body>Test content</body></html>'
        }
        mock_normalize.return_value = "Test content"
        mock_hash.return_value = "samehash123"  # Same hash
        
        # Execute
        result = lambda_handler({}, {})
        
        # Verify
        self.assertEqual(result['statusCode'], 200)
        body = json.loads(result['body'])
        self.assertEqual(body['urls_checked'], 1)
        self.assertEqual(body['changes_detected'], 0)
        
        # Verify email was NOT sent
        self.assertFalse(mock_send_email.called)
    
    @patch.dict(os.environ, {
        'URLS_JSON': '["https://example.com"]',
        'DDB_TABLE': 'test-table',
        'SES_FROM': 'noreply@test.com',
        'SES_TO': 'user@test.com',
        'USER_AGENT': 'Test/1.0',
        'LOG_LEVEL': 'INFO'
    })
    @patch('app.send_digest_email')
    @patch('app.update_state')
    @patch('app.get_state')
    @patch('app.fetch_url')
    @patch('app.normalize_html')
    @patch('app.compute_hash')
    def test_changed_url_triggers_notification(self, mock_hash, mock_normalize, mock_fetch,
                                               mock_get_state, mock_update, mock_send_email):
        """Test that a changed URL triggers notification."""
        # Setup mocks
        mock_get_state.return_value = {
            'last_hash': 'oldhash123',
            'normalized_text': 'Old content'
        }
        mock_fetch.return_value = {
            'status_code': 200,
            'content': '<html><body>New content</body></html>'
        }
        mock_normalize.return_value = "New content"
        mock_hash.return_value = "newhash456"
        
        # Execute
        result = lambda_handler({}, {})
        
        # Verify
        self.assertEqual(result['statusCode'], 200)
        body = json.loads(result['body'])
        self.assertEqual(body['changes_detected'], 1)
        
        # Verify email was sent
        self.assertTrue(mock_send_email.called)
        changes = mock_send_email.call_args[0][0]
        self.assertEqual(len(changes), 1)
        self.assertFalse(changes[0]['is_new'])
        self.assertEqual(changes[0]['previous_hash'], 'oldhash123')
    
    @patch.dict(os.environ, {
        'URLS_JSON': '["https://example1.com", "https://example2.com"]',
        'DDB_TABLE': 'test-table',
        'SES_FROM': 'noreply@test.com',
        'SES_TO': 'user@test.com',
        'USER_AGENT': 'Test/1.0',
        'LOG_LEVEL': 'INFO'
    })
    @patch('app.send_digest_email')
    @patch('app.update_state')
    @patch('app.get_state')
    @patch('app.fetch_url')
    @patch('app.normalize_html')
    @patch('app.compute_hash')
    def test_multiple_urls_digest(self, mock_hash, mock_normalize, mock_fetch,
                                  mock_get_state, mock_update, mock_send_email):
        """Test that multiple changed URLs result in a single digest email."""
        # Setup mocks - both URLs changed
        mock_get_state.return_value = None  # New URLs
        mock_fetch.return_value = {
            'status_code': 200,
            'content': '<html><body>Content</body></html>'
        }
        mock_normalize.return_value = "Content"
        mock_hash.return_value = "hash123"
        
        # Execute
        result = lambda_handler({}, {})
        
        # Verify
        self.assertEqual(result['statusCode'], 200)
        body = json.loads(result['body'])
        self.assertEqual(body['urls_checked'], 2)
        self.assertEqual(body['changes_detected'], 2)
        
        # Verify only ONE email was sent
        self.assertEqual(mock_send_email.call_count, 1)
        changes = mock_send_email.call_args[0][0]
        self.assertEqual(len(changes), 2)
    
    @patch.dict(os.environ, {
        'URLS_JSON': '["https://example.com"]',
        'DDB_TABLE': 'test-table',
        'SES_FROM': 'noreply@test.com',
        'SES_TO': 'user@test.com',
        'USER_AGENT': 'Test/1.0',
        'COOLDOWN_HOURS': '6',
        'LOG_LEVEL': 'INFO'
    })
    @patch('app.send_digest_email')
    @patch('app.update_state')
    @patch('app.get_state')
    @patch('app.fetch_url')
    @patch('app.normalize_html')
    @patch('app.compute_hash')
    def test_cooldown_blocks_notification_but_updates_state(self, mock_hash, mock_normalize, 
                                                           mock_fetch, mock_get_state, 
                                                           mock_update, mock_send_email):
        """Test that cooldown blocks notification but still updates state."""
        # Last notified 1 hour ago (within 6 hour cooldown)
        last_notified = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        
        # Setup mocks - URL changed but within cooldown
        mock_get_state.return_value = {
            'last_hash': 'oldhash123',
            'normalized_text': 'Old content',
            'last_notified_at': last_notified
        }
        mock_fetch.return_value = {
            'status_code': 200,
            'content': '<html><body>New content</body></html>',
            'etag': 'newtag'
        }
        mock_normalize.return_value = "New content"
        mock_hash.return_value = "newhash456"
        
        # Execute
        result = lambda_handler({}, {})
        
        # Verify
        self.assertEqual(result['statusCode'], 200)
        body = json.loads(result['body'])
        self.assertEqual(body['changes_detected'], 0)  # No notification sent
        
        # Verify email was NOT sent due to cooldown
        self.assertFalse(mock_send_email.called)
        
        # Verify state WAS updated with new hash (this is the critical bug fix)
        self.assertTrue(mock_update.called)
        update_call = mock_update.call_args[0][1]
        self.assertEqual(update_call['last_hash'], 'newhash456')
        self.assertEqual(update_call['normalized_text'], 'New content')
        self.assertIn('last_changed_at', update_call)
        self.assertNotIn('last_notified_at', update_call)  # Should not update notification time

    
    @patch.dict(os.environ, {
        'URLS_JSON': '[]',
        'DDB_TABLE': 'test-table',
        'SES_FROM': 'noreply@test.com',
        'SES_TO': 'user@test.com'
    })
    def test_no_urls_configured(self):
        """Test handler behavior with no URLs configured."""
        result = lambda_handler({}, {})
        
        self.assertEqual(result['statusCode'], 200)
        body = json.loads(result['body'])
        self.assertIn('No URLs', body['message'])


if __name__ == '__main__':
    unittest.main()
