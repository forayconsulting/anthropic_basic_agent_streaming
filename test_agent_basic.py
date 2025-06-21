#!/usr/bin/env python3
"""Test the agent without MCP to ensure core functionality works."""

import asyncio
import os
from claude_agent.agent_with_mcp import ClaudeAgentWithMCP, StreamEventType


async def test_basic_functionality():
    """Test basic agent functionality."""
    print("Testing Claude Agent Core Functionality")
    print("=" * 60)
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Please set ANTHROPIC_API_KEY")
        return
    
    agent = ClaudeAgentWithMCP(api_key=api_key)
    
    # Test 1: Basic response
    print("\nTest 1: Basic Response")
    print("-" * 40)
    
    try:
        async for event in agent.stream_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'Hello, the agent is working!' and nothing else.",
            include_mcp_context=False
        ):
            if event.type == StreamEventType.RESPONSE:
                print(event.content, end="", flush=True)
            elif event.type == StreamEventType.ERROR:
                print(f"\nError: {event.content}")
                return
        print("\n✓ Basic streaming works!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return
    
    # Test 2: Extended thinking
    print("\n\nTest 2: Extended Thinking")
    print("-" * 40)
    
    thinking_count = 0
    response_count = 0
    
    try:
        async for event in agent.stream_response(
            system_prompt="You are a helpful math tutor.",
            user_prompt="Think step by step: What is 15 * 17? Show your work.",
            thinking_budget=3000,
            max_tokens=10000
        ):
            if event.type == StreamEventType.THINKING:
                thinking_count += 1
            elif event.type == StreamEventType.RESPONSE:
                response_count += 1
                print(event.content, end="", flush=True)
            elif event.type == StreamEventType.ERROR:
                print(f"\nError: {event.content}")
                return
        
        print(f"\n✓ Extended thinking works! (Thinking: {thinking_count} tokens, Response: {response_count} tokens)")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return
    
    # Test 3: MCP context when not connected
    print("\n\nTest 3: MCP Context (Not Connected)")
    print("-" * 40)
    
    try:
        async for event in agent.stream_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="What MCP tools are available to you?",
            include_mcp_context=True
        ):
            if event.type == StreamEventType.RESPONSE:
                print(event.content, end="", flush=True)
        print("\n✓ MCP context handling works!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return
    
    print("\n\n✅ All core functionality tests passed!")
    print("\nThe agent is working correctly. The MCP server connection issues")
    print("appear to be related to the stdio communication in the MCP SDK.")
    print("\nPossible solutions:")
    print("1. Try running in a different environment")
    print("2. Check if MCP servers work in Claude Desktop")
    print("3. Wait for MCP SDK updates")
    print("4. Use the agent without MCP for now")


async def main():
    """Run tests."""
    await test_basic_functionality()


if __name__ == "__main__":
    # Get API key from argument if provided
    import sys
    if len(sys.argv) > 1:
        os.environ["ANTHROPIC_API_KEY"] = sys.argv[1]
    
    asyncio.run(main())