#!/usr/bin/env python3
"""Test Filesystem MCP server with Claude."""

import asyncio
import json
import os
from pathlib import Path
from claude_agent.agent_with_mcp import ClaudeAgentWithMCP, StreamEventType


async def test_filesystem():
    """Test filesystem MCP server."""
    print("Filesystem MCP Server Test with Claude")
    print("=" * 60)
    
    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Please set ANTHROPIC_API_KEY environment variable")
        return
    
    # Create a test file
    test_file = "/tmp/mcp_test_content.txt"
    with open(test_file, "w") as f:
        f.write("""This is a test file for MCP integration.
It contains multiple lines of text.
The MCP server should be able to read this file.
And Claude should be able to summarize its contents.""")
    print(f"Created test file: {test_file}")
    
    # Load Claude config
    config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    with open(config_path) as f:
        config = json.load(f)
    
    # Get filesystem server config
    fs_config = config['mcpServers']['filesystem']
    
    # Create agent
    agent = ClaudeAgentWithMCP(api_key=api_key)
    
    try:
        # Connect to filesystem server
        print("\nConnecting to filesystem MCP server...")
        await agent.connect_mcp(
            command=fs_config['command'],
            args=fs_config['args'],
            env=fs_config.get('env', {})
        )
        print("✓ Connected!")
        
        # Wait a moment for server to initialize
        await asyncio.sleep(2)
        
        # List tools
        tools = await agent.mcp_client.list_tools()
        print(f"\nAvailable tools: {[t.name for t in tools[:5]]}...")
        
        # Test 1: Ask Claude to read the file
        print(f"\n\nTest 1: Reading file {test_file}")
        print("-" * 60)
        
        async for event in agent.stream_response(
            system_prompt="You are a helpful assistant with filesystem access via MCP tools.",
            user_prompt=f"Please read the file at {test_file} and tell me what it contains.",
            include_mcp_context=True
        ):
            if event.type == StreamEventType.RESPONSE:
                print(event.content, end="", flush=True)
        
        # Test 2: Ask Claude to list files
        print("\n\n\nTest 2: Listing files in /tmp")
        print("-" * 60)
        
        async for event in agent.stream_response(
            system_prompt="You are a helpful assistant with filesystem access.",
            user_prompt="List the files in /tmp directory that start with 'mcp_'",
            include_mcp_context=True
        ):
            if event.type == StreamEventType.RESPONSE:
                print(event.content, end="", flush=True)
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n\nDisconnecting...")
        await agent.disconnect_mcp()
        print("✓ Disconnected")
        
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"✓ Cleaned up {test_file}")


async def main():
    """Run the test."""
    await test_filesystem()


if __name__ == "__main__":
    # Set API key if provided as argument
    import sys
    if len(sys.argv) > 1:
        os.environ["ANTHROPIC_API_KEY"] = sys.argv[1]
    
    asyncio.run(main())