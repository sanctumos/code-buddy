#!/usr/bin/env python3
"""
Code Buddy MCP Server (STDIO)

A lightweight Model Context Protocol (MCP) server that exposes tools for Cursor
to send messages to Letta agents. Uses STDIO transport for security (no open ports).

Copyright (C) 2025 SanctumOS

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Import Letta integration
from letta_integration import LettaClient

# Load environment variables
load_dotenv()

# Configure minimal logging - WARNING/ERROR only, to stderr
# This must happen before any other imports that might configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s',
    stream=sys.stderr,
    force=True
)

logger = logging.getLogger(__name__)

# Global Letta client instance
letta_client: LettaClient | None = None


def get_letta_client() -> LettaClient:
    """Get or create the Letta client instance."""
    global letta_client
    if letta_client is None:
        try:
            letta_client = LettaClient()
        except Exception as e:
            logger.error(f"Failed to initialize Letta client: {e}")
            raise
    return letta_client


def create_server() -> Server:
    """Create and configure the MCP server instance."""
    server = Server(name="code-buddy-mcp", version="0.1.0")
    
    # Register tools
    @server.list_tools()
    async def list_tools_handler():
        """Return the list of available tools."""
        return [
            Tool(
                name="send_message_to_letta",
                description="Send a message to the Letta agent. This allows Cursor to communicate with the same Letta agent that receives GitHub webhook events.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The message content to send to the Letta agent"
                        },
                        "agent_id": {
                            "type": "string",
                            "description": "Optional agent ID (defaults to configured agent)"
                        },
                        "identity_id": {
                            "type": "string",
                            "description": "Optional identity ID (defaults to 'code_buddy')"
                        }
                    },
                    "required": ["message"]
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool_handler(tool_name: str, arguments: dict):
        """Handle tool calls."""
        try:
            if tool_name == "send_message_to_letta":
                message = arguments.get("message")
                if not message:
                    return [TextContent(type="text", text=json.dumps({"error": "message is required"}))]
                
                agent_id = arguments.get("agent_id")
                identity_id = arguments.get("identity_id")
                
                # Prefix message to indicate it's from Cursor, not the normal user
                prefixed_message = f"[Username: @CursorAgent (User Commissioned), Telegram_Bot ID: N/A]\n\n{message}"
                
                # Get Letta client
                try:
                    client = get_letta_client()
                except Exception as e:
                    return [TextContent(type="text", text=json.dumps({"error": f"Letta client not available: {e}"}))]
                
                # Send message in thread pool (since Letta client is synchronous)
                loop = asyncio.get_event_loop()
                try:
                    response = await loop.run_in_executor(
                        None,
                        client.send_message,
                        prefixed_message,
                        agent_id,
                        identity_id
                    )
                    return [TextContent(type="text", text=json.dumps({"response": response}, indent=2))]
                except Exception as e:
                    logger.error(f"Error sending message to Letta: {e}")
                    return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
            
            else:
                return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {tool_name}"}))]
        
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
    
    return server


async def main():
    """Main entry point for STDIO mode."""
    # Initialize Letta client early to fail fast if misconfigured
    try:
        get_letta_client()
    except Exception as e:
        logger.error(f"Failed to initialize Letta client: {e}")
        logger.error("Make sure LETTA_BASE_URL and LETTA_AGENT_ID are set in your environment")
        sys.exit(1)
    
    # Create MCP server
    server = create_server()
    
    try:
        # Use stdio transport - this handles stdin/stdout wrapping
        # The context manager yields (read_stream, write_stream)
        async with stdio_server() as (read_stream, write_stream):
            # Run the server with the stdio streams
            # server.run() will block and handle all JSON-RPC messages
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    except ExceptionGroup as eg:
        # Handle ExceptionGroup from anyio TaskGroup (Python 3.11+)
        # On Windows, we get OSError [Errno 22] when flushing stdout
        # This is a known issue - the server works fine, but flush fails on exit
        if sys.platform == 'win32':
            flush_errors = [e for e in eg.exceptions if isinstance(e, OSError) and e.errno == 22]
            if len(flush_errors) == len(eg.exceptions):
                # All errors are Windows flush errors - non-fatal
                # The server has already done its job successfully
                logger.warning("Windows stdout flush issue (non-fatal, server completed successfully)")
                return  # Exit gracefully
        # If not all errors are flush errors, re-raise
        raise
    except BaseExceptionGroup as eg:
        # Handle BaseExceptionGroup (Python 3.11+ alternative)
        if sys.platform == 'win32':
            flush_errors = [e for e in eg.exceptions if isinstance(e, OSError) and e.errno == 22]
            if len(flush_errors) == len(eg.exceptions):
                logger.warning("Windows stdout flush issue (non-fatal, server completed successfully)")
                return
        raise
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        pass
    except Exception as e:
        # Log errors to stderr only - never to stdout
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
