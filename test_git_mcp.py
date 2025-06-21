#!/usr/bin/env python3
"""Test Git MCP server (Python-based, no npx)."""

import asyncio
import json
import os
from pathlib import Path
from claude_agent.agent_with_mcp import ClaudeAgentWithMCP, StreamEventType


async def test_git_server():
    """Test the Git MCP server."""
    print("Git MCP Server Test")
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
    
    # Get Git server config
    git_config = config['mcpServers']['git']
    
    print(f"Server config:")
    print(f"  Command: {git_config['command']}")
    print(f"  Args: {git_config['args']}")
    
    # Create agent
    agent = ClaudeAgentWithMCP(api_key=api_key)
    
    try:
        # Connect to Git server
        print("\nConnecting to Git MCP server...")
        await agent.connect_mcp(
            command=git_config['command'],
            args=git_config['args'],
            env=git_config.get('env', {})
        )
        print("✓ Connected!")
        
        # List available tools
        tools = await agent.mcp_client.list_tools()
        print(f"\nAvailable tools ({len(tools)}):")
        for tool in tools[:10]:  # Show first 10 tools
            print(f"  - {tool.name}: {tool.description[:50]}...")
        
        # Test: Ask about git status
        print("\n\nAsking Claude about git repository status...")
        print("-" * 60)
        
        async for event in agent.stream_response(
            system_prompt="You are a helpful assistant with access to Git tools.",
            user_prompt="Can you check the git status of the current repository and tell me what branch we're on?",
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
    await test_git_server()


if __name__ == "__main__":
    # Set API key if provided as argument
    import sys
    if len(sys.argv) > 1:
        os.environ["ANTHROPIC_API_KEY"] = sys.argv[1]
    
    asyncio.run(main())