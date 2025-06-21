#!/usr/bin/env python3
"""Test SQLite MCP server."""

import asyncio
import json
import os
from pathlib import Path
from claude_agent.agent_with_mcp import ClaudeAgentWithMCP, StreamEventType


async def test_sqlite_server():
    """Test the SQLite MCP server."""
    print("SQLite MCP Server Test")
    print("=" * 60)
    
    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Please set ANTHROPIC_API_KEY environment variable")
        return
    
    # Load Claude config
    config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    with open(config_path) as f:
        config = json.load(f)
    
    # Get SQLite server config
    sqlite_config = config['mcpServers']['sqlite']
    
    print(f"Server config:")
    print(f"  Command: {sqlite_config['command']}")
    print(f"  Args: {sqlite_config['args']}")
    
    # Check if the binary exists
    if not os.path.exists(sqlite_config['command']):
        print(f"\n❌ SQLite MCP server not found at: {sqlite_config['command']}")
        print("Please install it first")
        return
    
    # Create agent
    agent = ClaudeAgentWithMCP(api_key=api_key)
    
    try:
        # Connect to SQLite server
        print("\nConnecting to SQLite MCP server...")
        await agent.connect_mcp(
            command=sqlite_config['command'],
            args=sqlite_config['args'],
            env=sqlite_config.get('env', {})
        )
        print("✓ Connected!")
        
        # Wait a moment for initialization
        await asyncio.sleep(2)
        
        # List available tools
        tools = await agent.mcp_client.list_tools()
        print(f"\nAvailable tools ({len(tools)}):")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description[:50]}...")
        
        # Test: Ask about database schema
        print("\n\nAsking Claude about database schema...")
        print("-" * 60)
        
        async for event in agent.stream_response(
            system_prompt="You are a helpful assistant with access to SQLite database tools.",
            user_prompt="Can you list the tables in the database and describe what each one is for?",
            include_mcp_context=True
        ):
            if event.type == StreamEventType.RESPONSE:
                print(event.content, end="", flush=True)
            elif event.type == StreamEventType.ERROR:
                print(f"\nError: {event.content}")
        
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\nDisconnecting...")
        await agent.disconnect_mcp()
        print("✓ Disconnected")


async def main():
    """Run the test."""
    await test_sqlite_server()


if __name__ == "__main__":
    # Set API key if provided as argument
    import sys
    if len(sys.argv) > 1:
        os.environ["ANTHROPIC_API_KEY"] = sys.argv[1]
    
    asyncio.run(main())