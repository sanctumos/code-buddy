#!/usr/bin/env python3
"""
GitHub Webhook Processor

A Flask-based webhook processor that receives GitHub organization events,
validates HMAC signatures, and processes them.

Copyright (C) 2025 AnimusUNO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import os
import hmac
import hashlib
import json
from typing import Dict, Any, Optional
from datetime import datetime

import structlog
from flask import Flask, request, jsonify, abort
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Flask app configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

# Configuration
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'animus_webhook_secret_2024')
PORT = int(os.getenv('PORT', 5000))
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'


class WebhookProcessor:
    """Main webhook processing class"""
    
    def __init__(self):
        self.logger = logger.bind(component="webhook_processor")
        self.event_count = 0
        self.start_time = datetime.utcnow()
    
    def verify_signature(self, payload_body: bytes, signature_header: str) -> bool:
        """
        Verify GitHub webhook signature using HMAC-SHA256
        
        Args:
            payload_body: Raw request body
            signature_header: X-Hub-Signature-256 header value
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        if not signature_header:
            self.logger.warning("Missing signature header")
            return False
        
        try:
            # Extract signature from "sha256=abc123..." format
            sha_name, signature = signature_header.split('=')
            if sha_name != 'sha256':
                self.logger.warning("Invalid signature method", method=sha_name)
                return False
            
            # Compute expected signature
            expected = hmac.new(
                WEBHOOK_SECRET.encode(),
                payload_body,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures securely
            is_valid = hmac.compare_digest(expected, signature)
            
            if not is_valid:
                self.logger.warning("Invalid webhook signature")
            
            return is_valid
            
        except Exception as e:
            self.logger.error("Signature verification error", error=str(e))
            return False
    
    def parse_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and normalize GitHub webhook event
        
        Args:
            payload: GitHub webhook payload
            
        Returns:
            Dict: Normalized event data
        """
        try:
            event_type = request.headers.get('X-GitHub-Event', 'unknown')
            delivery_id = request.headers.get('X-GitHub-Delivery', 'unknown')
            
            # Extract common fields
            normalized_event = {
                'event_type': event_type,
                'delivery_id': delivery_id,
                'timestamp': datetime.utcnow().isoformat(),
                'action': payload.get('action'),
                'repository': self._extract_repository_info(payload),
                'sender': self._extract_sender_info(payload),
                'organization': self._extract_organization_info(payload),
                'raw_payload': payload  # Keep original for debugging
            }
            
            # Add event-specific data
            if event_type == 'push':
                normalized_event.update(self._parse_push_event(payload))
            elif event_type == 'issues':
                normalized_event.update(self._parse_issue_event(payload))
            elif event_type == 'pull_request':
                normalized_event.update(self._parse_pull_request_event(payload))
            elif event_type == 'release':
                normalized_event.update(self._parse_release_event(payload))
            
            return normalized_event
            
        except Exception as e:
            self.logger.error("Event parsing error", error=str(e), payload=payload)
            return {
                'event_type': 'parse_error',
                'error': str(e),
                'raw_payload': payload
            }
    
    def _extract_repository_info(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract repository information from payload"""
        repo = payload.get('repository', {})
        return {
            'id': repo.get('id'),
            'name': repo.get('name'),
            'full_name': repo.get('full_name'),
            'url': repo.get('html_url'),
            'private': repo.get('private', False),
            'default_branch': repo.get('default_branch')
        }
    
    def _extract_sender_info(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract sender information from payload"""
        sender = payload.get('sender', {})
        return {
            'id': sender.get('id'),
            'login': sender.get('login'),
            'name': sender.get('name'),
            'email': sender.get('email'),
            'avatar_url': sender.get('avatar_url')
        }
    
    def _extract_organization_info(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract organization information from payload"""
        org = payload.get('organization', {})
        return {
            'id': org.get('id'),
            'login': org.get('login'),
            'name': org.get('name'),
            'url': org.get('html_url')
        }
    
    def _parse_push_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse push event specific data"""
        return {
            'ref': payload.get('ref'),
            'before': payload.get('before'),
            'after': payload.get('after'),
            'commits': [
                {
                    'id': commit.get('id'),
                    'message': commit.get('message'),
                    'author': commit.get('author', {}).get('name'),
                    'url': commit.get('url')
                }
                for commit in payload.get('commits', [])
            ],
            'pusher': payload.get('pusher', {}).get('name')
        }
    
    def _parse_issue_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse issue event specific data"""
        issue = payload.get('issue', {})
        return {
            'issue_id': issue.get('id'),
            'number': issue.get('number'),
            'title': issue.get('title'),
            'body': issue.get('body'),
            'state': issue.get('state'),
            'labels': [label.get('name') for label in issue.get('labels', [])],
            'assignees': [assignee.get('login') for assignee in issue.get('assignees', [])],
            'url': issue.get('html_url')
        }
    
    def _parse_pull_request_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse pull request event specific data"""
        pr = payload.get('pull_request', {})
        return {
            'pr_id': pr.get('id'),
            'number': pr.get('number'),
            'title': pr.get('title'),
            'body': pr.get('body'),
            'state': pr.get('state'),
            'merged': pr.get('merged'),
            'mergeable': pr.get('mergeable'),
            'head': {
                'ref': pr.get('head', {}).get('ref'),
                'sha': pr.get('head', {}).get('sha')
            },
            'base': {
                'ref': pr.get('base', {}).get('ref'),
                'sha': pr.get('base', {}).get('sha')
            },
            'url': pr.get('html_url')
        }
    
    def _parse_release_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse release event specific data"""
        release = payload.get('release', {})
        return {
            'release_id': release.get('id'),
            'tag_name': release.get('tag_name'),
            'name': release.get('name'),
            'body': release.get('body'),
            'draft': release.get('draft'),
            'prerelease': release.get('prerelease'),
            'url': release.get('html_url')
        }
    
    def should_process_event(self, event: Dict[str, Any]) -> bool:
        """
        Determine if event should be processed based on filtering rules
        
        Args:
            event: Normalized event data
            
        Returns:
            bool: True if event should be processed
        """
        # Skip parse errors
        if event.get('event_type') == 'parse_error':
            return False
        
        # Skip test repositories (optional filtering)
        repo_name = event.get('repository', {}).get('name', '').lower()
        if 'test' in repo_name:
            self.logger.info("Skipping test repository", repo=repo_name)
            return False
        
        # Process all other events
        return True
    
    def process_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process normalized event
        
        Args:
            event: Normalized event data
            
        Returns:
            Dict: Processing result
        """
        self.event_count += 1
        
        # Log event processing
        self.logger.info(
            "Event processed",
            event_type=event.get('event_type'),
            action=event.get('action'),
            repository=event.get('repository', {}).get('full_name'),
            sender=event.get('sender', {}).get('login'),
            event_count=self.event_count
        )
        
        # TODO: Add custom event processing logic here
        # This is where you would integrate with your own systems
        
        return {
            'status': 'processed',
            'event_id': event.get('delivery_id'),
            'processed_at': datetime.utcnow().isoformat(),
            'event_count': self.event_count
        }


# Initialize webhook processor
processor = WebhookProcessor()


@app.route('/webhook', methods=['POST'])
def webhook():
    """Main webhook endpoint"""
    try:
        # Get raw payload and signature
        payload_body = request.get_data()
        signature_header = request.headers.get('X-Hub-Signature-256')
        
        # Verify signature
        if not processor.verify_signature(payload_body, signature_header):
            logger.warning("Invalid webhook signature", ip=request.remote_addr)
            abort(403, "Invalid signature")
        
        # Parse JSON payload
        try:
            payload = request.get_json()
        except Exception as e:
            logger.error("Invalid JSON payload", error=str(e))
            abort(400, "Invalid JSON")
        
        # Parse and normalize event
        event = processor.parse_event(payload)
        
        # Check if event should be processed
        if not processor.should_process_event(event):
            logger.info("Event skipped by filter", event_type=event.get('event_type'))
            return jsonify({'status': 'skipped'}), 200
        
        # Process event
        result = processor.process_event(event)
        
        logger.info("Webhook processed successfully", result=result)
        return jsonify(result), 200
        
    except Exception as e:
        logger.error("Webhook processing error", error=str(e))
        abort(500, "Internal server error")


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    uptime = (datetime.utcnow() - processor.start_time).total_seconds()
    
    return jsonify({
        'status': 'healthy',
        'uptime_seconds': uptime,
        'events_processed': processor.event_count,
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@app.route('/stats', methods=['GET'])
def stats():
    """Statistics endpoint"""
    uptime = (datetime.utcnow() - processor.start_time).total_seconds()
    
    return jsonify({
        'uptime_seconds': uptime,
        'events_processed': processor.event_count,
        'start_time': processor.start_time.isoformat(),
        'webhook_secret_configured': bool(WEBHOOK_SECRET),
        'debug_mode': DEBUG
    }), 200


@app.errorhandler(403)
def forbidden(error):
    """Handle 403 Forbidden errors"""
    logger.warning("Forbidden request", error=str(error), ip=request.remote_addr)
    return jsonify({'error': 'Forbidden'}), 403


@app.errorhandler(400)
def bad_request(error):
    """Handle 400 Bad Request errors"""
    logger.warning("Bad request", error=str(error), ip=request.remote_addr)
    return jsonify({'error': 'Bad Request'}), 400


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors"""
    logger.error("Internal server error", error=str(error))
    return jsonify({'error': 'Internal Server Error'}), 500


if __name__ == '__main__':
    logger.info(
        "Starting GitHub webhook processor",
        port=PORT,
        debug=DEBUG,
        webhook_secret_configured=bool(WEBHOOK_SECRET)
    )
    
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)

