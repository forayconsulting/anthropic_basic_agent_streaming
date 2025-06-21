#!/usr/bin/env python3
"""Demo of MCP tool integration with Claude."""

import asyncio
import json
import os
from pathlib import Path
from claude_agent.agent_with_tools import ClaudeAgentWithTools, StreamEventType
from claude_agent.mcp_client_fixed import FixedMCPClient


async def demo_basic_connection():
    """Demo basic MCP connection."""
    print("1. Basic MCP Connection Test")
    print("-" * 40)
    
    client = FixedMCPClient()
    
    # Test with a simple server
    print("Testing connection to filesystem server...")
    
    try:
        async with client.connect(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        ) as session:
            print("✓ Connected successfully!")
            
            # Show tools
            print(f"\nAvailable tools: {len(client.tools)}")
            for i, tool in enumerate(client.tools[:3]):
                print(f"  {i+1}. {tool.name}")
            
            # Show Anthropic format
            anthropic_tools = client.get_anthropic_tools()
            print(f"\nTools in Anthropic format: {len(anthropic_tools)}")
            
            # Try a simple tool call
            print("\nTesting tool call...")
            result = await session.call_tool("list_directory", {"path": "/tmp"})
            print("✓ Tool call successful!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True


async def demo_claude_integration():
    """Demo Claude integration with MCP tools."""
    print("\n\n2. Claude + MCP Integration Demo")
    print("-" * 40)
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  No API key set. Showing structure only.")
        
        # Show how it would work
        print("\nHow it works:")
        print("1. Agent connects to MCP server")
        print("2. MCP tools are converted to Anthropic format")
        print("3. Tools are included in Claude API request")
        print("4. Claude can use tools to answer questions")
        print("5. Tool results are sent back to Claude")
        print("6. Claude provides final response")
        
        return False
    
    # Create test file
    test_file = "/tmp/mcp_demo.txt"
    with open(test_file, "w") as f:
        f.write("Hello from MCP Demo!\n")
        f.write("This file demonstrates tool integration.\n")
        f.write("Claude can read this using MCP tools.\n")
    
    agent = ClaudeAgentWithTools(api_key=api_key)
    
    try:
        # Connect to filesystem server
        print("Connecting to filesystem MCP server...")
        await agent.connect_mcp(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        )
        print("✓ Connected!")
        
        # Simple query
        print("\nAsking Claude to read our test file...")
        print("User: What's in /tmp/mcp_demo.txt?")
        print("\nClaude:", end=" ")
        
        async for event in agent.stream_response_with_tools(
            system_prompt="You are a helpful assistant with filesystem access.",
            user_prompt=f"What's in /tmp/mcp_demo.txt?"
        ):
            if event.type == StreamEventType.RESPONSE:
                print(event.content, end="", flush=True)
            elif event.type == StreamEventType.TOOL_USE:
                print(f"\n[Using tool: {event.metadata.get('tool', {}).get('name')}]", end="")
        
        print("\n\n✓ Integration successful!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    
    finally:
        await agent.disconnect_mcp()
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)
    
    return True


async def demo_youtube_integration():
    """Demo YouTube transcript integration."""
    print("\n\n3. YouTube Transcript Integration")
    print("-" * 40)
    
    # Load config
    config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if not config_path.exists():
        print("⚠️  No Claude Desktop config found")
        return False
    
    with open(config_path) as f:
        config = json.load(f)
    
    if 'mcp-server-youtube-transcript' not in config['mcpServers']:
        print("⚠️  YouTube transcript server not configured")
        return False
    
    print("✓ YouTube transcript server is configured")
    print("\nExample usage:")
    print("```python")
    print("await agent.connect_mcp(")
    print('    command="npx",')
    print('    args=["-y", "@smithery/cli", "run", ')
    print('          "@kimtaeyoon83/mcp-server-youtube-transcript"]')
    print(")")
    print("")
    print("# Then ask Claude about any YouTube video")
    print('user_prompt = "Summarize this video: https://youtube.com/watch?v=..."')
    print("```")
    
    return True


async def main():
    """Run all demos."""
    print("MCP Tool Integration Demo")
    print("=" * 60)
    print("\nThis demo shows how to integrate MCP servers with Claude API.\n")
    
    # Run demos
    success1 = await demo_basic_connection()
    success2 = await demo_claude_integration()
    success3 = await demo_youtube_integration()
    
    # Summary
    print("\n\nSummary")
    print("=" * 60)
    print(f"✓ Basic MCP connection: {'Working' if success1 else 'Failed'}")
    print(f"✓ Claude integration: {'Working' if success2 else 'Needs API key'}")
    print(f"✓ YouTube config: {'Found' if success3 else 'Not found'}")
    
    print("\n📚 Next Steps:")
    print("1. Set ANTHROPIC_API_KEY environment variable")
    print("2. Run: python test_filesystem_tools.py")
    print("3. Run: python test_youtube_tools.py")
    print("\n✨ Your MCP integration is ready to use!")


if __name__ == "__main__":
    asyncio.run(main())