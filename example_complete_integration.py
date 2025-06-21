#!/usr/bin/env python3
"""Complete example of MCP tool integration with Claude."""

import asyncio
import json
import os
from pathlib import Path
from claude_agent.agent_tools_fixed import ClaudeAgentWithToolsFixed, StreamEventType


async def demonstrate_complete_integration():
    """Demonstrate the complete MCP + Claude integration."""
    
    print("🤖 Claude + MCP Tool Integration Demo")
    print("=" * 60)
    print("\nThis demo shows Claude using MCP tools to interact with external systems.\n")
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  No API key found. Set ANTHROPIC_API_KEY to run the demo.")
        print("\nExample:")
        print("export ANTHROPIC_API_KEY=your-key-here")
        print("python example_complete_integration.py")
        return
    
    # Create agent
    agent = ClaudeAgentWithToolsFixed(api_key=api_key)
    
    # Example 1: Filesystem Tools
    print("\n📁 Example 1: Filesystem Integration")
    print("-" * 40)
    
    try:
        await agent.connect_mcp(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/Users/claytonchancey/Desktop"]
        )
        print("✓ Connected to filesystem MCP server")
        
        await asyncio.sleep(2)
        
        print("\nAvailable tools:")
        for tool in agent.mcp_manager.tools[:5]:
            print(f"  - {tool.name}: {tool.description[:50]}...")
        
        print("\n💬 Conversation:")
        print("User: What files are on my Desktop? Just list the first 5.")
        print("\nClaude: ", end="")
        
        async for event in agent.stream_response_with_tools(
            system_prompt="You are a helpful assistant with filesystem access.",
            user_prompt="What files are on my Desktop? Just list the first 5."
        ):
            if event.type == StreamEventType.RESPONSE:
                print(event.content, end="", flush=True)
            elif event.type == StreamEventType.TOOL_USE:
                print(f"\n  [🔧 Using: {event.metadata.get('tool_name')}]", end="")
        
        await agent.disconnect_mcp()
        print("\n\n✅ Filesystem integration successful!")
        
    except Exception as e:
        print(f"\n❌ Filesystem error: {e}")
        await agent.disconnect_mcp()
    
    # Example 2: YouTube Transcripts
    print("\n\n📺 Example 2: YouTube Transcript Integration")
    print("-" * 40)
    
    # Check if YouTube server is configured
    config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        
        if 'mcp-server-youtube-transcript' in config['mcpServers']:
            yt_config = config['mcpServers']['mcp-server-youtube-transcript']
            
            try:
                print("Connecting to YouTube transcript server...")
                await agent.connect_mcp(
                    command=yt_config['command'],
                    args=yt_config['args']
                )
                print("✓ Connected!")
                
                await asyncio.sleep(3)
                
                print("\n💬 Conversation:")
                print("User: What's this video about? https://www.youtube.com/watch?v=dQw4w9WgXcQ")
                print("\nClaude: ", end="")
                
                async for event in agent.stream_response_with_tools(
                    system_prompt="You are a helpful assistant with YouTube tools.",
                    user_prompt="What's this video about? https://www.youtube.com/watch?v=dQw4w9WgXcQ (just give a brief answer)"
                ):
                    if event.type == StreamEventType.RESPONSE:
                        print(event.content, end="", flush=True)
                    elif event.type == StreamEventType.TOOL_USE:
                        print(f"\n  [🔧 Using: {event.metadata.get('tool_name')}]", end="")
                
                await agent.disconnect_mcp()
                print("\n\n✅ YouTube integration successful!")
                
            except Exception as e:
                print(f"\n❌ YouTube error: {e}")
                await agent.disconnect_mcp()
        else:
            print("YouTube transcript server not configured in Claude Desktop")
    
    # Summary
    print("\n\n🎉 Integration Complete!")
    print("=" * 60)
    print("\n✨ What we demonstrated:")
    print("  1. Claude successfully connects to MCP servers")
    print("  2. MCP tools are automatically available to Claude")
    print("  3. Claude can use tools to answer questions")
    print("  4. Tool results are seamlessly integrated into responses")
    print("\n📚 You can now use any MCP server with Claude!")
    print("\nTry these servers:")
    print("  - @modelcontextprotocol/server-github")
    print("  - @modelcontextprotocol/server-sqlite") 
    print("  - @modelcontextprotocol/server-postgresql")
    print("  - Your own custom MCP servers!")


async def main():
    """Run the demonstration."""
    await demonstrate_complete_integration()


if __name__ == "__main__":
    import sys
    
    # Allow API key as command line argument
    if len(sys.argv) > 1:
        os.environ["ANTHROPIC_API_KEY"] = sys.argv[1]
    
    asyncio.run(main())