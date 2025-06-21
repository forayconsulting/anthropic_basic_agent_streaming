#!/usr/bin/env python3
"""Simple MCP test."""

import asyncio
import json
from pathlib import Path
from claude_agent.mcp_client_simple import SimpleMCPClient


async def test_filesystem_server():
    """Test the filesystem MCP server."""
    print("Testing Filesystem MCP Server")
    print("=" * 60)
    
    client = SimpleMCPClient()
    
    # Get server config
    config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    with open(config_path) as f:
        config = json.load(f)
    
    fs_config = config['mcpServers']['filesystem']
    
    try:
        async with client.create_session(
            command=fs_config['command'],
            args=fs_config['args'],
            env=fs_config.get('env', {})
        ) as session:
            print("✓ Connected to filesystem server!")
            
            # Show tools
            print(f"\nTools ({len(client.tools)}):")
            for tool in client.tools[:5]:
                print(f"  - {tool.name}: {tool.description[:60]}...")
            
            # Show resources
            print(f"\nResources ({len(client.resources)}):")
            for resource in client.resources[:5]:
                print(f"  - {resource.uri}: {resource.description[:60]}...")
            
            # Try to call a tool
            if any(tool.name == "read_file" for tool in client.tools):
                print("\n\nTesting read_file tool...")
                
                # Create a test file
                test_file = "/tmp/mcp_test.txt"
                with open(test_file, "w") as f:
                    f.write("Hello from MCP test!\nThis is working correctly.")
                
                # Call the tool
                result = await session.call_tool("read_file", {"path": test_file})
                
                print("Tool result:")
                if hasattr(result, 'content') and result.content:
                    for content in result.content:
                        if hasattr(content, 'text'):
                            print(f"  {content.text}")
                
            # Get context
            print("\n\nContext for Claude:")
            print("-" * 40)
            print(client.get_context()[:500] + "...")
            
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


async def test_with_agent():
    """Test MCP with the agent."""
    import os
    from claude_agent.agent_with_mcp import ClaudeAgentWithMCP, StreamEventType
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set")
        return
    
    print("\n\nTesting with Claude Agent")
    print("=" * 60)
    
    # Get server config
    config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    with open(config_path) as f:
        config = json.load(f)
    
    fs_config = config['mcpServers']['filesystem']
    
    agent = ClaudeAgentWithMCP(api_key=api_key)
    
    try:
        # Connect to MCP
        print("Connecting agent to MCP server...")
        await agent.connect_mcp(
            command=fs_config['command'],
            args=fs_config['args'],
            env=fs_config.get('env', {})
        )
        print("✓ Connected!")
        
        # Ask about available tools
        print("\nAsking Claude about MCP tools...")
        print("-" * 40)
        
        response_tokens = []
        async for event in agent.stream_response(
            system_prompt="You are a helpful assistant with access to MCP tools.",
            user_prompt="What MCP tools do you have available? List the first 3 tools with their descriptions.",
            include_mcp_context=True
        ):
            if event.type == StreamEventType.RESPONSE:
                response_tokens.append(event.content)
                print(event.content, end="", flush=True)
        
        print(f"\n\nResponse length: {len(''.join(response_tokens))} characters")
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
    
    finally:
        await agent.disconnect_mcp()
        print("\n✓ Disconnected from MCP")


async def main():
    """Run all tests."""
    await test_filesystem_server()
    
    print("\n\nWould you like to test with Claude Agent? This will use your API key.")
    print("Run with --agent flag to test with agent")
    
    import sys
    if '--agent' in sys.argv:
        await test_with_agent()


if __name__ == "__main__":
    asyncio.run(main())