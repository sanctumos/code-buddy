#!/usr/bin/env python3
"""
Code Buddy MCP Server

A lightweight Model Context Protocol (MCP) server that exposes GitHub webhook events
to Sanctum and Letta AI agents through Cursor.

Copyright (C) 2025 SanctumOS

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import argparse
import asyncio
import json
import logging
import os
import signal
from typing import Dict, Any

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import shared event store
from event_store import get_event_store

# Global event store instance (shared with webhook processor)
event_store_instance = get_event_store()


def create_server() -> Server:
    """Create and configure the MCP server instance."""
    server = Server(name="code-buddy-mcp", version="0.1.0")
    
    # Register tools
    @server.list_tools()
    async def list_tools_handler():
        """Return the list of available tools."""
        return [
            Tool(
                name="get_recent_events",
                description="Get recent GitHub webhook events. Can filter by event type, repository, and time range.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "event_type": {
                            "type": "string",
                            "description": "Filter by event type (e.g., 'issues', 'push', 'pull_request')"
                        },
                        "repository": {
                            "type": "string",
                            "description": "Filter by repository name or full name"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of events to return (default: 50, max: 100)",
                            "default": 50,
                            "minimum": 1,
                            "maximum": 100
                        },
                        "since": {
                            "type": "string",
                            "description": "ISO timestamp to filter events since (e.g., '2025-01-15T10:00:00Z')"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="get_event_stats",
                description="Get statistics about stored GitHub events including counts by type and repositories.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="get_event_by_id",
                description="Get a specific event by its delivery ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "delivery_id": {
                            "type": "string",
                            "description": "The delivery ID of the event to retrieve"
                        }
                    },
                    "required": ["delivery_id"]
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool_handler(tool_name: str, arguments: dict):
        """Handle tool calls."""
        try:
            if tool_name == "get_recent_events":
                # Run in thread pool since event_store is synchronous
                loop = asyncio.get_event_loop()
                events = await loop.run_in_executor(
                    None,
                    event_store_instance.get_events,
                    arguments.get("event_type"),
                    arguments.get("repository"),
                    min(arguments.get("limit", 50), 100),
                    arguments.get("since")
                )
                result = {
                    "count": len(events),
                    "events": events
                }
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif tool_name == "get_event_stats":
                # Run in thread pool since event_store is synchronous
                loop = asyncio.get_event_loop()
                stats = await loop.run_in_executor(None, event_store_instance.get_stats)
                return [TextContent(type="text", text=json.dumps(stats, indent=2))]
            
            elif tool_name == "get_event_by_id":
                delivery_id = arguments.get("delivery_id")
                if not delivery_id:
                    return [TextContent(type="text", text=json.dumps({"error": "delivery_id is required"}))]
                
                # Run in thread pool since event_store is synchronous
                loop = asyncio.get_event_loop()
                event = await loop.run_in_executor(
                    None,
                    event_store_instance.get_event_by_id,
                    delivery_id
                )
                
                if event:
                    return [TextContent(type="text", text=json.dumps(event, indent=2))]
                else:
                    return [TextContent(type="text", text=json.dumps({"error": f"Event with delivery_id '{delivery_id}' not found"}))]
            
            else:
                return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {tool_name}"}))]
        
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
    
    return server


async def async_main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Code Buddy MCP Server - Lightweight MCP server for GitHub webhook events"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", "8001")),
        help="Port to run the server on (default: 8001 or MCP_PORT env var)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("MCP_HOST", "127.0.0.1"),
        help="Host to bind to (default: 127.0.0.1 or MCP_HOST env var)"
    )
    parser.add_argument(
        "--allow-external",
        action="store_true",
        help="Allow external connections (default: localhost-only for security)"
    )
    
    args = parser.parse_args()
    
    # Determine host binding
    if args.allow_external:
        host = "0.0.0.0"
        logger.warning("⚠️  WARNING: External connections are allowed. This may pose security risks.")
    else:
        host = args.host
        if host == "127.0.0.1":
            logger.info("🔒 Security: Server bound to localhost only. Use --allow-external for network access.")
    
    logger.info(f"Starting Code Buddy MCP Server on {host}:{args.port}...")
    
    # Create MCP server
    server = create_server()
    
    # Create SSE transport
    sse_transport = SseServerTransport("/messages/")
    
    # Create Starlette app with SSE endpoints
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import Response
    
    async def sse_endpoint(request):
        """SSE connection endpoint."""
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0],  # read_stream
                streams[1],  # write_stream
                server.create_initialization_options()
            )
        return Response()
    
    # Create Starlette app
    app = Starlette(routes=[
        Route("/sse", sse_endpoint, methods=["GET"]),
        Mount("/messages/", app=sse_transport.handle_post_message),
    ])
    
    # Start server
    logger.info("Starting server with SSE transport...")
    import uvicorn
    
    config = uvicorn.Config(
        app,
        host=host,
        port=args.port,
        log_level="info"
    )
    
    server_instance = uvicorn.Server(config)
    
    # Handle shutdown signals
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        server_instance.should_exit = True
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start server
    await server_instance.serve()


def main():
    """Synchronous entry point."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

