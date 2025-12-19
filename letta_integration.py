#!/usr/bin/env python3
"""
Letta Message Sender

This module handles sending messages to Letta agents from both the webhook processor
and the MCP server. It provides a clean interface for communicating with Letta agents.

Copyright (C) 2025 SanctumOS

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import os
import logging
from typing import Optional, Dict, Any
from letta_client import Letta, MessageCreate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class LettaClient:
    """Client for sending messages to Letta agents"""
    
    def __init__(self):
        """Initialize the Letta client with environment configuration"""
        self.base_url = os.getenv('LETTA_BASE_URL')
        self.token = os.getenv('LETTA_TOKEN')
        self.project = os.getenv('LETTA_PROJECT')
        self.agent_id = os.getenv('LETTA_AGENT_ID')
        self.identity_id = os.getenv('LETTA_IDENTITY_ID', 'code_buddy')
        
        # Validate required configuration
        if not self.base_url:
            raise ValueError("LETTA_BASE_URL environment variable is required")
        
        if not self.agent_id:
            raise ValueError("LETTA_AGENT_ID environment variable is required")
        
        # Create the client
        self.client = Letta(
            base_url=self.base_url,
            token=self.token,
            project=self.project
        )
        
        logger.info(f"Letta client initialized for agent {self.agent_id}")
    
    def send_message(self, content: str, agent_id: Optional[str] = None, identity_id: Optional[str] = None) -> str:
        """
        Send a message to a Letta agent
        
        Args:
            content: The message content to send
            agent_id: The agent ID (defaults to configured agent)
            identity_id: The user identity ID (defaults to configured identity)
        
        Returns:
            The agent's response content
        """
        agent_id = agent_id or self.agent_id
        identity_id = identity_id or self.identity_id
        
        # Create message
        message = MessageCreate(
            role="user",
            content=content,
            sender_id=identity_id
        )
        
        logger.info(f"Sending message to Letta agent {agent_id}: {content[:100]}...")
        
        try:
            # Send message to agent
            response = self.client.agents.messages.create(
                agent_id=agent_id,
                messages=[message]
            )
            
            # Extract response content
            if response.messages:
                last_message = response.messages[-1]
                if hasattr(last_message, 'content'):
                    response_content = last_message.content
                else:
                    response_content = str(last_message)
                
                logger.info(f"Received response from Letta: {response_content[:100]}...")
                return response_content
            else:
                logger.warning("No response messages received from Letta")
                return "No response received"
                
        except Exception as e:
            logger.error(f"Error sending message to Letta: {e}")
            raise
    
    def send_github_event(self, event_data: Dict[str, Any]) -> str:
        """
        Send a GitHub webhook event to the Letta agent
        
        Args:
            event_data: The normalized GitHub event data
        
        Returns:
            The agent's response
        """
        # Format the event data for the agent
        event_summary = self._format_event_for_letta(event_data)
        
        return self.send_message(event_summary)
    
    def _format_event_for_letta(self, event_data: Dict[str, Any]) -> str:
        """
        Format GitHub event data into a readable message for Letta
        
        Args:
            event_data: The normalized GitHub event data
        
        Returns:
            Formatted message string
        """
        event_type = event_data.get('event_type', 'unknown')
        action = event_data.get('action', 'unknown')
        repository = event_data.get('repository', {})
        sender = event_data.get('sender', {})
        
        repo_name = repository.get('full_name', 'unknown repository')
        sender_name = sender.get('login', 'unknown user')
        
        # Create a summary message
        message = f"GitHub Event: {event_type} - {action}\n"
        message += f"Repository: {repo_name}\n"
        message += f"User: {sender_name}\n"
        
        # Add specific details based on event type
        if event_type == 'issues':
            issue = event_data.get('issue', {})
            message += f"Issue #{issue.get('number', '?')}: {issue.get('title', 'No title')}\n"
            if issue.get('body'):
                message += f"Description: {issue.get('body', '')[:200]}...\n"
        
        elif event_type == 'pull_request':
            pr = event_data.get('pr', {})
            message += f"PR #{pr.get('number', '?')}: {pr.get('title', 'No title')}\n"
            if pr.get('body'):
                message += f"Description: {pr.get('body', '')[:200]}...\n"
        
        elif event_type == 'push':
            commits = event_data.get('commits', [])
            message += f"Commits: {len(commits)} new commits\n"
            if commits:
                message += f"Latest: {commits[0].get('message', 'No message')[:100]}...\n"
        
        # Add full event data for context
        message += f"\nFull event data: {event_data}"
        
        return message

