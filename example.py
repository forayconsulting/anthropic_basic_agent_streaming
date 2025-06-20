#!/usr/bin/env python3
"""Example usage of Claude Agent."""

import asyncio
import os
from claude_agent.agent import ClaudeAgent, StreamEventType


async def main():
    """Example of using Claude Agent."""
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Please set ANTHROPIC_API_KEY environment variable")
        return
    
    # Create agent
    agent = ClaudeAgent(api_key=api_key)
    
    # Example 1: Simple streaming response
    print("=== Example 1: Simple Response ===")
    async for event in agent.stream_response(
        system_prompt="You are a helpful assistant.",
        user_prompt="What is the capital of France?"
    ):
        if event.type == StreamEventType.RESPONSE:
            print(event.content, end="", flush=True)
        elif event.type == StreamEventType.ERROR:
            print(f"\nError: {event.content}")
    print("\n")
    
    # Example 2: With extended thinking
    print("=== Example 2: Extended Thinking ===")
    async for event in agent.stream_response(
        system_prompt="You are a math tutor.",
        user_prompt="Explain why 0.999... equals 1",
        thinking_budget=5000,
        max_tokens=10000
    ):
        if event.type == StreamEventType.THINKING:
            print(f"[Thinking] {event.content}")
        elif event.type == StreamEventType.RESPONSE:
            print(event.content, end="", flush=True)
    print("\n")
    
    # Example 3: With MCP server (if you have one)
    print("=== Example 3: With MCP (Optional) ===")
    try:
        # Connect to MCP server (adjust command as needed)
        await agent.connect_mcp("python", ["-m", "my_mcp_server"])
        
        async for event in agent.stream_response(
            system_prompt="You are a helpful assistant with access to tools.",
            user_prompt="Use available tools to help me."
        ):
            if event.type == StreamEventType.RESPONSE:
                print(event.content, end="", flush=True)
        
        await agent.disconnect_mcp()
    except Exception as e:
        print(f"MCP example skipped: {e}")
    print("\n")
    
    # Example 4: With conversation history
    print("=== Example 4: Conversation History ===")
    history = [
        {"role": "user", "content": "My name is Alice"},
        {"role": "assistant", "content": "Nice to meet you, Alice!"}
    ]
    
    async for event in agent.stream_response(
        system_prompt="You are a friendly assistant.",
        user_prompt="What's my name?",
        conversation_history=history
    ):
        if event.type == StreamEventType.RESPONSE:
            print(event.content, end="", flush=True)
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())