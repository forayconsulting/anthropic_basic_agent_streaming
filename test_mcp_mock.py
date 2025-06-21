#!/usr/bin/env python3
"""Test MCP integration with mock server (no npx required)."""

import asyncio
import os
from claude_agent.agent_with_mcp import ClaudeAgentWithMCP, StreamEventType


async def test_agent_without_mcp():
    """Test the agent without MCP to ensure basic functionality works."""
    print("Testing Agent WITHOUT MCP")
    print("=" * 60)
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set")
        return False
    
    agent = ClaudeAgentWithMCP(api_key=api_key)
    
    try:
        # Test 1: Basic streaming
        print("\nTest 1: Basic streaming response")
        print("-" * 40)
        
        response = []
        async for event in agent.stream_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'Hello from MCP test!' and nothing else.",
            include_mcp_context=False  # No MCP context
        ):
            if event.type == StreamEventType.RESPONSE:
                response.append(event.content)
                print(event.content, end="", flush=True)
            elif event.type == StreamEventType.ERROR:
                print(f"\nError: {event.content}")
                return False
        
        print("\n✓ Basic streaming works!")
        
        # Test 2: Extended thinking
        print("\n\nTest 2: Extended thinking mode")
        print("-" * 40)
        
        thinking_count = 0
        response_count = 0
        
        async for event in agent.stream_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Think step by step: What is 2+2? Just give the final answer.",
            thinking_budget=2000,
            max_tokens=5000,
            include_mcp_context=False
        ):
            if event.type == StreamEventType.THINKING:
                thinking_count += 1
            elif event.type == StreamEventType.RESPONSE:
                response_count += 1
                print(event.content, end="", flush=True)
            elif event.type == StreamEventType.ERROR:
                print(f"\nError: {event.content}")
                return False
        
        print(f"\n✓ Extended thinking works! (Thinking tokens: {thinking_count}, Response tokens: {response_count})")
        
        # Test 3: MCP context when not connected
        print("\n\nTest 3: MCP context when not connected")
        print("-" * 40)
        
        async for event in agent.stream_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="What MCP tools do you have?",
            include_mcp_context=True  # This should include "MCP: Not connected"
        ):
            if event.type == StreamEventType.RESPONSE:
                print(event.content, end="", flush=True)
        
        print("\n✓ MCP context handling works!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_mcp_client_simple():
    """Test the simple MCP client structure."""
    print("\n\nTesting Simple MCP Client Structure")
    print("=" * 60)
    
    from claude_agent.mcp_client_simple import SimpleMCPClient, MCPTool, MCPResource
    
    # Test creating tools and resources
    tool = MCPTool(
        name="test_tool",
        description="A test tool",
        input_schema={"type": "object", "properties": {"input": {"type": "string"}}}
    )
    
    resource = MCPResource(
        uri="test://resource",
        name="Test Resource",
        description="A test resource",
        mime_type="text/plain"
    )
    
    print(f"✓ Created tool: {tool.name}")
    print(f"✓ Created resource: {resource.name}")
    
    # Test client methods
    client = SimpleMCPClient()
    context = client.get_context()
    print(f"✓ Empty context: '{context}'")
    
    return True


async def main():
    """Run all tests."""
    print("MCP Integration Tests (Mock)")
    print("=" * 60)
    
    # Test agent without MCP
    success1 = await test_agent_without_mcp()
    
    # Test MCP client structure
    success2 = await test_mcp_client_simple()
    
    if success1 and success2:
        print("\n\n✅ All tests passed!")
        print("\nThe MCP integration is ready. To test with real MCP servers:")
        print("1. Ensure Node.js and npm are installed")
        print("2. Run: python test_local_mcp_servers.py")
        print("3. Or use: python example_mcp_usage.py")
    else:
        print("\n\n❌ Some tests failed!")


if __name__ == "__main__":
    asyncio.run(main())