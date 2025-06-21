#!/usr/bin/env python3
"""Debug tool integration."""

import asyncio
import json
import os
from claude_agent.agent_with_tools import ClaudeAgentWithTools, StreamEventType
from claude_agent.mcp_client_fixed import FixedMCPClient


async def debug_tools():
    """Debug tool availability and format."""
    
    # First check MCP connection directly
    print("1. Testing MCP Connection")
    print("-" * 40)
    
    client = FixedMCPClient()
    
    async with client.connect(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    ) as session:
        print("✓ Connected to MCP server")
        
        # Show tools
        print(f"\nMCP Tools ({len(client.tools)}):")
        for tool in client.tools[:3]:
            print(f"\n- {tool.name}")
            print(f"  Description: {tool.description[:100]}...")
            print(f"  Schema: {json.dumps(tool.input_schema, indent=4)[:200]}...")
        
        # Show Anthropic format
        anthropic_tools = client.get_anthropic_tools()
        print(f"\n\nAnthropicformat ({len(anthropic_tools)}):")
        for tool in anthropic_tools[:1]:
            print(json.dumps(tool, indent=2)[:400] + "...")
    
    # Now test with agent
    print("\n\n2. Testing Agent with Tools")
    print("-" * 40)
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("No API key set")
        return
    
    agent = ClaudeAgentWithTools(api_key=api_key)
    
    # Connect
    await agent.connect_mcp(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    )
    print("✓ Agent connected to MCP")
    
    # Check tools
    tools = agent.mcp_manager.tools
    print(f"\nAgent has {len(tools)} tools available")
    
    # Test with explicit tool request
    print("\nAsking Claude to explicitly use a tool...")
    
    # Create test file
    with open("/tmp/debug_test.txt", "w") as f:
        f.write("Debug test content\nLine 2\nLine 3")
    
    events = []
    async for event in agent.stream_response_with_tools(
        system_prompt="You are a helpful assistant with filesystem tools. Always use the read_file tool when asked to read files.",
        user_prompt="Please use the read_file tool to read /tmp/debug_test.txt and tell me exactly what it contains."
    ):
        events.append(event)
        if event.type == StreamEventType.RESPONSE:
            print(event.content, end="", flush=True)
        elif event.type == StreamEventType.TOOL_USE:
            print(f"\n[TOOL USE: {event.content}]")
        elif event.type == StreamEventType.TOOL_RESULT:
            print(f"\n[TOOL RESULT: {event.content[:50]}...]")
    
    # Summary
    print(f"\n\nEvent summary:")
    event_types = {}
    for event in events:
        event_types[event.type.value] = event_types.get(event.type.value, 0) + 1
    
    for event_type, count in event_types.items():
        print(f"  {event_type}: {count}")
    
    await agent.disconnect_mcp()
    
    # Cleanup
    for f in ["/tmp/debug_test.txt", "/tmp/mcp_test.txt"]:
        if os.path.exists(f):
            os.remove(f)


if __name__ == "__main__":
    asyncio.run(debug_tools())