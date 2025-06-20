#!/usr/bin/env python3
"""Debug script to test API connection."""

import asyncio
import os
import httpx
from claude_agent.agent import ClaudeAgent, StreamEventType


async def debug_test():
    """Test API connection with detailed error reporting."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    print("Debug Test")
    print("=" * 50)
    print(f"API Key present: {'Yes' if api_key else 'No'}")
    print(f"API Key length: {len(api_key) if api_key else 0}")
    print(f"API Key starts with: {api_key[:15]}..." if api_key else "No API key")
    
    # Test 1: Direct API call
    print("\nTest 1: Direct API call")
    print("-" * 30)
    
    try:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        request_data = {
            "model": "claude-opus-4-20250514",
            "messages": [{"role": "user", "content": "Say 'test' and nothing else"}],
            "max_tokens": 10
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                json=request_data,
                headers=headers,
                timeout=30.0
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            response_json = response.json()
            print(f"Response body: {response_json}")
            
    except Exception as e:
        print(f"ERROR in direct API call: {type(e).__name__}: {e}")
    
    # Test 2: Using the agent
    print("\n\nTest 2: Using the agent")
    print("-" * 30)
    
    try:
        agent = ClaudeAgent(api_key=api_key)
        event_count = 0
        error_count = 0
        
        async for event in agent.stream_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'hello' and nothing else"
        ):
            event_count += 1
            print(f"Event {event_count}: Type={event.type.value}, Content='{event.content}'")
            
            if event.type == StreamEventType.ERROR:
                error_count += 1
                print(f"Error details: {event.metadata}")
        
        print(f"\nTotal events received: {event_count}")
        print(f"Errors: {error_count}")
        
    except Exception as e:
        print(f"ERROR in agent test: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_test())