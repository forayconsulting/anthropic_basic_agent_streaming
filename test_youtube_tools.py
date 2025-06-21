#!/usr/bin/env python3
"""Test YouTube Transcript MCP server with tool integration."""

import asyncio
import json
import os
from pathlib import Path
from claude_agent.agent_with_tools import ClaudeAgentWithTools, StreamEventType


async def test_youtube_with_tools():
    """Test YouTube transcript server with full tool integration."""
    print("YouTube Transcript MCP Server Test - Full Tool Integration")
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
    
    # Get YouTube transcript server config
    yt_config = config['mcpServers']['mcp-server-youtube-transcript']
    
    print(f"Server config:")
    print(f"  Command: {yt_config['command']}")
    print(f"  Args: {yt_config['args']}")
    
    # Create agent
    agent = ClaudeAgentWithTools(api_key=api_key)
    
    try:
        # Connect to YouTube transcript server
        print("\nConnecting to YouTube transcript MCP server...")
        await agent.connect_mcp(
            command=yt_config['command'],
            args=yt_config['args'],
            env=yt_config.get('env', {})
        )
        print("✓ Connected!")
        
        # Wait for server to initialize
        await asyncio.sleep(3)
        
        # Check available tools
        tools = agent.mcp_manager.tools
        print(f"\nAvailable tools ({len(tools)}):")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
            print(f"    Schema: {json.dumps(tool.input_schema, indent=6)}")
        
        # Test 1: Ask Claude to get transcript
        video_url = "https://www.youtube.com/watch?v=ynMg7-QfL10"
        print(f"\n\nTest 1: Getting transcript for {video_url}")
        print("-" * 60)
        
        response_parts = []
        tool_uses = []
        tool_results = []
        
        async for event in agent.stream_response_with_tools(
            system_prompt="You are a helpful assistant with access to YouTube transcript tools.",
            user_prompt=f"Please get the transcript for this YouTube video and summarize the main points: {video_url}"
        ):
            if event.type == StreamEventType.RESPONSE:
                response_parts.append(event.content)
                print(event.content, end="", flush=True)
            elif event.type == StreamEventType.TOOL_USE:
                print(f"\n[Tool Use] {event.content}")
                tool_uses.append(event.metadata)
            elif event.type == StreamEventType.TOOL_RESULT:
                print(f"\n[Tool Result] {event.content[:100]}...")
                tool_results.append(event.metadata)
            elif event.type == StreamEventType.ERROR:
                print(f"\n[Error] {event.content}")
        
        print(f"\n\nSummary:")
        print(f"  Response length: {len(''.join(response_parts))} characters")
        print(f"  Tool uses: {len(tool_uses)}")
        print(f"  Tool results: {len(tool_results)}")
        
        # Test 2: Ask about a different video
        print("\n\n\nTest 2: Another video")
        print("-" * 60)
        
        video_url2 = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll :)
        
        async for event in agent.stream_response_with_tools(
            system_prompt="You are a helpful assistant with YouTube tools.",
            user_prompt=f"What is this video about? {video_url2} (Just give me a brief one-line answer)"
        ):
            if event.type == StreamEventType.RESPONSE:
                print(event.content, end="", flush=True)
        
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\nDisconnecting...")
        await agent.disconnect_mcp()
        print("✓ Disconnected")


async def test_direct_mcp_connection():
    """Test direct MCP connection without API calls."""
    print("\n\nDirect MCP Connection Test")
    print("=" * 60)
    
    from claude_agent.mcp_client_fixed import FixedMCPClient
    
    # Load config
    config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    with open(config_path) as f:
        config = json.load(f)
    
    yt_config = config['mcpServers']['mcp-server-youtube-transcript']
    
    client = FixedMCPClient()
    
    try:
        print("Connecting directly to MCP server...")
        async with client.connect(
            command=yt_config['command'],
            args=yt_config['args']
        ) as session:
            print("✓ Connected!")
            
            # List tools
            tools = client.tools
            print(f"\nTools: {[t.name for t in tools]}")
            
            # Try to call a tool if available
            if tools and any(t.name == "get_transcript" for t in tools):
                print("\nCalling get_transcript tool...")
                result = await session.call_tool(
                    "get_transcript",
                    {"url": "https://www.youtube.com/watch?v=ynMg7-QfL10"}
                )
                print(f"Result preview: {str(result)[:200]}...")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run tests."""
    print("MCP Tool Integration Tests")
    print("=" * 60)
    
    # Test direct connection first
    await test_direct_mcp_connection()
    
    # Then test with Claude
    print("\n" + "=" * 60)
    await test_youtube_with_tools()


if __name__ == "__main__":
    # Set API key if provided
    import sys
    if len(sys.argv) > 1:
        os.environ["ANTHROPIC_API_KEY"] = sys.argv[1]
    
    asyncio.run(main())