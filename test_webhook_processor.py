#!/usr/bin/env python3
"""
GitHub Webhook Processor - Test Suite

Comprehensive tests for the webhook processor including unit tests,
integration tests, and webhook signature verification tests.
"""

import os
import json
import hmac
import hashlib
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Set test environment
os.environ['WEBHOOK_SECRET'] = 'test_secret_123'
os.environ['FLASK_SECRET_KEY'] = 'test-flask-secret'
os.environ['DEBUG'] = 'True'

from webhook_processor import app, WebhookProcessor, WEBHOOK_SECRET


@pytest.fixture
def client():
    """Flask test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def processor():
    """Webhook processor instance"""
    return WebhookProcessor()


@pytest.fixture
def sample_payload():
    """Sample GitHub webhook payload"""
    return {
        "action": "opened",
        "issue": {
            "id": 123456789,
            "number": 42,
            "title": "Test Issue",
            "body": "This is a test issue",
            "state": "open",
            "user": {
                "login": "testuser",
                "id": 987654321
            },
            "html_url": "https://github.com/test/repo/issues/42"
        },
        "repository": {
            "id": 111222333,
            "name": "test-repo",
            "full_name": "test/test-repo",
            "html_url": "https://github.com/test/test-repo",
            "private": False,
            "default_branch": "main"
        },
        "sender": {
            "login": "testuser",
            "id": 987654321,
            "avatar_url": "https://avatars.githubusercontent.com/u/987654321"
        },
        "organization": {
            "login": "test-org",
            "id": 444555666,
            "html_url": "https://github.com/test-org"
        }
    }


@pytest.fixture
def sample_push_payload():
    """Sample push event payload"""
    return {
        "ref": "refs/heads/main",
        "before": "abc123",
        "after": "def456",
        "commits": [
            {
                "id": "def456",
                "message": "Test commit",
                "author": {
                    "name": "Test User"
                },
                "url": "https://github.com/test/repo/commit/def456"
            }
        ],
        "pusher": {
            "name": "testuser"
        },
        "repository": {
            "id": 111222333,
            "name": "test-repo",
            "full_name": "test/test-repo",
            "html_url": "https://github.com/test/test-repo",
            "private": False,
            "default_branch": "main"
        },
        "sender": {
            "login": "testuser",
            "id": 987654321
        }
    }


def create_signature(payload_body: bytes, secret: str) -> str:
    """Create HMAC signature for test payload"""
    signature = hmac.new(
        secret.encode(),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


class TestWebhookProcessor:
    """Test webhook processor functionality"""
    
    def test_signature_verification_valid(self, processor, sample_payload):
        """Test valid signature verification"""
        payload_body = json.dumps(sample_payload).encode()
        signature = create_signature(payload_body, WEBHOOK_SECRET)
        
        assert processor.verify_signature(payload_body, signature) is True
    
    def test_signature_verification_invalid(self, processor, sample_payload):
        """Test invalid signature verification"""
        payload_body = json.dumps(sample_payload).encode()
        invalid_signature = "sha256=invalid_signature"
        
        assert processor.verify_signature(payload_body, invalid_signature) is False
    
    def test_signature_verification_missing(self, processor, sample_payload):
        """Test missing signature"""
        payload_body = json.dumps(sample_payload).encode()
        
        assert processor.verify_signature(payload_body, None) is False
        assert processor.verify_signature(payload_body, "") is False
    
    def test_signature_verification_wrong_method(self, processor, sample_payload):
        """Test wrong signature method"""
        payload_body = json.dumps(sample_payload).encode()
        wrong_signature = "sha1=abc123"
        
        assert processor.verify_signature(payload_body, wrong_signature) is False
    
    def test_parse_issue_event(self, processor, sample_payload):
        """Test issue event parsing"""
        with patch('webhook_processor.request') as mock_request:
            mock_request.headers.get.side_effect = lambda key: {
                'X-GitHub-Event': 'issues',
                'X-GitHub-Delivery': 'test-delivery-id'
            }.get(key)
            
            event = processor.parse_event(sample_payload)
            
            assert event['event_type'] == 'issues'
            assert event['action'] == 'opened'
            assert event['delivery_id'] == 'test-delivery-id'
            assert event['issue']['title'] == 'Test Issue'
            assert event['repository']['name'] == 'test-repo'
            assert event['sender']['login'] == 'testuser'
    
    def test_parse_push_event(self, processor, sample_push_payload):
        """Test push event parsing"""
        with patch('webhook_processor.request') as mock_request:
            mock_request.headers.get.side_effect = lambda key: {
                'X-GitHub-Event': 'push',
                'X-GitHub-Delivery': 'test-delivery-id'
            }.get(key)
            
            event = processor.parse_event(sample_push_payload)
            
            assert event['event_type'] == 'push'
            assert event['ref'] == 'refs/heads/main'
            assert event['before'] == 'abc123'
            assert event['after'] == 'def456'
            assert len(event['commits']) == 1
            assert event['commits'][0]['message'] == 'Test commit'
    
    def test_should_process_event(self, processor):
        """Test event filtering logic"""
        # Normal event should be processed
        normal_event = {
            'event_type': 'issues',
            'repository': {'name': 'normal-repo'}
        }
        assert processor.should_process_event(normal_event) is True
        
        # Parse error should be skipped
        error_event = {
            'event_type': 'parse_error',
            'error': 'test error'
        }
        assert processor.should_process_event(error_event) is False
        
        # Test repository should be skipped
        test_event = {
            'event_type': 'issues',
            'repository': {'name': 'test-repo'}
        }
        assert processor.should_process_event(test_event) is False
    
    def test_process_event(self, processor):
        """Test event processing"""
        event = {
            'event_type': 'issues',
            'action': 'opened',
            'repository': {'full_name': 'test/repo'},
            'sender': {'login': 'testuser'},
            'delivery_id': 'test-id'
        }
        
        result = processor.process_event(event)
        
        assert result['status'] == 'processed'
        assert result['event_id'] == 'test-id'
        assert processor.event_count == 1


class TestWebhookEndpoints:
    """Test webhook endpoints"""
    
    def test_webhook_valid_signature(self, client, sample_payload):
        """Test webhook endpoint with valid signature"""
        payload_body = json.dumps(sample_payload).encode()
        signature = create_signature(payload_body, WEBHOOK_SECRET)
        
        response = client.post(
            '/webhook',
            data=payload_body,
            headers={
                'Content-Type': 'application/json',
                'X-Hub-Signature-256': signature,
                'X-GitHub-Event': 'issues',
                'X-GitHub-Delivery': 'test-delivery'
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'processed'
    
    def test_webhook_invalid_signature(self, client, sample_payload):
        """Test webhook endpoint with invalid signature"""
        payload_body = json.dumps(sample_payload).encode()
        
        response = client.post(
            '/webhook',
            data=payload_body,
            headers={
                'Content-Type': 'application/json',
                'X-Hub-Signature-256': 'sha256=invalid',
                'X-GitHub-Event': 'issues'
            }
        )
        
        assert response.status_code == 403
    
    def test_webhook_missing_signature(self, client, sample_payload):
        """Test webhook endpoint with missing signature"""
        payload_body = json.dumps(sample_payload).encode()
        
        response = client.post(
            '/webhook',
            data=payload_body,
            headers={
                'Content-Type': 'application/json',
                'X-GitHub-Event': 'issues'
            }
        )
        
        assert response.status_code == 403
    
    def test_webhook_invalid_json(self, client):
        """Test webhook endpoint with invalid JSON"""
        payload_body = b"invalid json"
        signature = create_signature(payload_body, WEBHOOK_SECRET)
        
        response = client.post(
            '/webhook',
            data=payload_body,
            headers={
                'Content-Type': 'application/json',
                'X-Hub-Signature-256': signature,
                'X-GitHub-Event': 'issues'
            }
        )
        
        assert response.status_code == 400
    
    def test_webhook_test_repository_skipped(self, client, sample_payload):
        """Test that test repositories are skipped"""
        # Modify payload to have test repository
        sample_payload['repository']['name'] = 'test-repo'
        
        payload_body = json.dumps(sample_payload).encode()
        signature = create_signature(payload_body, WEBHOOK_SECRET)
        
        response = client.post(
            '/webhook',
            data=payload_body,
            headers={
                'Content-Type': 'application/json',
                'X-Hub-Signature-256': signature,
                'X-GitHub-Event': 'issues',
                'X-GitHub-Delivery': 'test-delivery'
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'skipped'
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'uptime_seconds' in data
        assert 'events_processed' in data
    
    def test_stats_endpoint(self, client):
        """Test statistics endpoint"""
        response = client.get('/stats')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'uptime_seconds' in data
        assert 'events_processed' in data
        assert 'start_time' in data
        assert 'webhook_secret_configured' in data


class TestEventParsing:
    """Test event parsing for different event types"""
    
    def test_pull_request_event_parsing(self, processor):
        """Test pull request event parsing"""
        pr_payload = {
            "action": "opened",
            "pull_request": {
                "id": 123456789,
                "number": 42,
                "title": "Test PR",
                "body": "Test PR body",
                "state": "open",
                "merged": False,
                "mergeable": True,
                "head": {
                    "ref": "feature-branch",
                    "sha": "abc123"
                },
                "base": {
                    "ref": "main",
                    "sha": "def456"
                },
                "html_url": "https://github.com/test/repo/pull/42"
            },
            "repository": {
                "id": 111222333,
                "name": "test-repo",
                "full_name": "test/test-repo"
            },
            "sender": {
                "login": "testuser",
                "id": 987654321
            }
        }
        
        with patch('webhook_processor.request') as mock_request:
            mock_request.headers.get.side_effect = lambda key: {
                'X-GitHub-Event': 'pull_request',
                'X-GitHub-Delivery': 'test-delivery-id'
            }.get(key)
            
            event = processor.parse_event(pr_payload)
            
            assert event['event_type'] == 'pull_request'
            assert event['action'] == 'opened'
            assert event['pr']['title'] == 'Test PR'
            assert event['pr']['number'] == 42
            assert event['pr']['head']['ref'] == 'feature-branch'
            assert event['pr']['base']['ref'] == 'main'
    
    def test_release_event_parsing(self, processor):
        """Test release event parsing"""
        release_payload = {
            "action": "published",
            "release": {
                "id": 123456789,
                "tag_name": "v1.0.0",
                "name": "Release v1.0.0",
                "body": "First release",
                "draft": False,
                "prerelease": False,
                "html_url": "https://github.com/test/repo/releases/tag/v1.0.0"
            },
            "repository": {
                "id": 111222333,
                "name": "test-repo",
                "full_name": "test/test-repo"
            },
            "sender": {
                "login": "testuser",
                "id": 987654321
            }
        }
        
        with patch('webhook_processor.request') as mock_request:
            mock_request.headers.get.side_effect = lambda key: {
                'X-GitHub-Event': 'release',
                'X-GitHub-Delivery': 'test-delivery-id'
            }.get(key)
            
            event = processor.parse_event(release_payload)
            
            assert event['event_type'] == 'release'
            assert event['action'] == 'published'
            assert event['release']['tag_name'] == 'v1.0.0'
            assert event['release']['name'] == 'Release v1.0.0'
            assert event['release']['draft'] is False


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])

