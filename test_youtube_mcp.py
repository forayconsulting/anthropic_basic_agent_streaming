#!/usr/bin/env python3
"""Test YouTube Transcript MCP server."""

import asyncio
import json
import os
from pathlib import Path
from claude_agent.agent_with_mcp import ClaudeAgentWithMCP, StreamEventType


async def test_youtube_transcript():
    """Test the YouTube transcript MCP server."""
    print("YouTube Transcript MCP Server Test")
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
    agent = ClaudeAgentWithMCP(api_key=api_key)
    
    try:
        # Connect to YouTube transcript server
        print("\nConnecting to YouTube transcript MCP server...")
        await agent.connect_mcp(
            command=yt_config['command'],
            args=yt_config['args'],
            env=yt_config.get('env', {})
        )
        print("✓ Connected!")
        
        # List available tools
        tools = await agent.mcp_client.list_tools()
        print(f"\nAvailable tools ({len(tools)}):")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
            if tool.input_schema:
                print(f"    Input: {json.dumps(tool.input_schema, indent=6)}")
        
        # Get YouTube video transcript
        video_url = "https://www.youtube.com/watch?v=ynMg7-QfL10"
        print(f"\n\nFetching transcript for: {video_url}")
        print("-" * 60)
        
        # Ask Claude to get and summarize the transcript
        async for event in agent.stream_response(
            system_prompt="You are a helpful assistant with access to YouTube transcript tools. Use the available tools to fetch transcripts when asked.",
            user_prompt=f"Please fetch the transcript for this YouTube video and give me a brief summary of what it's about: {video_url}",
            include_mcp_context=True
        ):
            if event.type == StreamEventType.RESPONSE:
                print(event.content, end="", flush=True)
            elif event.type == StreamEventType.ERROR:
                print(f"\nError: {event.content}")
        
        print("\n\n" + "=" * 60)
        
        # Try calling the tool directly if it exists
        if any(tool.name == "get_transcript" for tool in tools):
            print("\nDirect tool call test:")
            print("-" * 40)
            
            async for event in agent.call_mcp_tool(
                tool_name="get_transcript",
                arguments={"url": video_url},
                result_prompt="Based on this transcript, what are the main topics discussed in this video? Please provide a bulleted list."
            ):
                if event.type == StreamEventType.RESPONSE:
                    print(event.content, end="", flush=True)
                elif event.type == StreamEventType.ERROR:
                    print(f"\nError: {event.content}")
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n\nDisconnecting...")
        await agent.disconnect_mcp()
        print("✓ Disconnected")


async def main():
    """Run the test."""
    await test_youtube_transcript()


if __name__ == "__main__":
    # Set API key if provided as argument
    import sys
    if len(sys.argv) > 1:
        os.environ["ANTHROPIC_API_KEY"] = sys.argv[1]
    
    asyncio.run(main())