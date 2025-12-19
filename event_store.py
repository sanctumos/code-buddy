#!/usr/bin/env python3
"""
Shared Event Store

A simple event store that can be used by both the webhook processor and MCP server.
Uses file-based persistence for cross-process communication.
"""

import json
import logging
from collections import deque
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class EventStore:
    """Simple event store with file persistence."""
    
    def __init__(self, max_size: int = 1000, persist_file: str = "events.json"):
        self.events: deque = deque(maxlen=max_size)
        self.persist_file = Path(persist_file)
        self.max_size = max_size
        self._load_events()
    
    def _load_events(self):
        """Load events from persistence file if it exists."""
        if self.persist_file.exists():
            try:
                with open(self.persist_file, 'r') as f:
                    events = json.load(f)
                    # Only load up to max_size
                    events_to_load = events[-self.max_size:]
                    self.events.extend(events_to_load)
                logger.info(f"Loaded {len(self.events)} events from {self.persist_file}")
            except Exception as e:
                logger.warning(f"Failed to load events from {self.persist_file}: {e}")
    
    def _save_events(self):
        """Save events to persistence file."""
        try:
            # Create directory if it doesn't exist
            self.persist_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.persist_file, 'w') as f:
                json.dump(list(self.events), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save events to {self.persist_file}: {e}")
    
    def add_event(self, event: Dict[str, Any]):
        """Add an event to the store (thread-safe for file operations)."""
        self.events.append(event)
        self._save_events()
        logger.debug(f"Added event: {event.get('event_type')} - {event.get('delivery_id')}")
    
    def get_events(
        self,
        event_type: Optional[str] = None,
        repository: Optional[str] = None,
        limit: int = 50,
        since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query events with filters."""
        results = []
        
        # Parse since timestamp if provided
        since_dt = None
        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            except:
                pass
        
        for event in reversed(self.events):  # Most recent first
            # Filter by event type
            if event_type and event.get('event_type') != event_type:
                continue
            
            # Filter by repository
            if repository:
                repo_full_name = event.get('repository', {}).get('full_name', '')
                repo_name = event.get('repository', {}).get('name', '')
                if repository.lower() not in repo_full_name.lower() and repository.lower() not in repo_name.lower():
                    continue
            
            # Filter by timestamp
            if since_dt:
                event_timestamp = event.get('timestamp')
                if event_timestamp:
                    try:
                        event_dt = datetime.fromisoformat(event_timestamp.replace('Z', '+00:00'))
                        if event_dt < since_dt:
                            continue
                    except:
                        pass
            
            results.append(event)
            if len(results) >= limit:
                break
        
        return results
    
    def get_event_by_id(self, delivery_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific event by delivery ID."""
        for event in self.events:
            if event.get("delivery_id") == delivery_id:
                return event
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored events."""
        event_types = {}
        repositories = set()
        
        for event in self.events:
            event_type = event.get('event_type', 'unknown')
            event_types[event_type] = event_types.get(event_type, 0) + 1
            
            repo_name = event.get('repository', {}).get('full_name')
            if repo_name:
                repositories.add(repo_name)
        
        return {
            'total_events': len(self.events),
            'event_types': event_types,
            'unique_repositories': len(repositories),
            'repositories': sorted(list(repositories))
        }


# Global singleton instance
_global_store: Optional[EventStore] = None


def get_event_store() -> EventStore:
    """Get or create the global event store instance."""
    global _global_store
    if _global_store is None:
        import os
        _global_store = EventStore(
            max_size=int(os.getenv('EVENT_STORE_SIZE', '1000')),
            persist_file=os.getenv('EVENT_STORE_FILE', 'events.json')
        )
    return _global_store


