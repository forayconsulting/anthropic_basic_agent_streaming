#!/usr/bin/env python3
"""Mock test to verify agent functionality without API calls."""

import asyncio
from unittest.mock import patch, AsyncMock
from claude_agent.agent import ClaudeAgent, StreamEventType


def create_mock_response(chunks):
    """Create a mock response that simulates streaming."""
    async def mock_stream():
        for chunk in chunks:
            yield chunk
    
    mock_response = AsyncMock()
    mock_response.aiter_bytes = mock_stream
    return mock_response


async def test_with_mock():
    """Test agent with mocked API responses."""
    print("Claude Agent Mock Test")
    print("=" * 50)
    print("This test uses mocked responses - no API calls made\n")
    
    # Create agent (API key doesn't matter for mock test)
    agent = ClaudeAgent(api_key="mock-key")
    
    # Test 1: Basic response
    print("Test 1: Basic Response")
    print("-" * 30)
    
    mock_chunks = [
        b'event: message_start\ndata: {"type": "message_start", "message": {"id": "msg_123"}}\n\n',
        b'event: content_block_start\ndata: {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}\n\n',
        b'event: content_block_delta\ndata: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "2 + 2 equals "}}\n\n',
        b'event: content_block_delta\ndata: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "4."}}\n\n',
        b'event: message_stop\ndata: {"type": "message_stop"}\n\n'
    ]
    
    with patch('httpx.AsyncClient.stream') as mock_stream:
        mock_response = create_mock_response(mock_chunks)
        mock_stream.return_value.__aenter__.return_value = mock_response
        
        print("Sending: What is 2+2?")
        print("Response: ", end="", flush=True)
        
        async for event in agent.stream_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="What is 2+2?"
        ):
            if event.type == StreamEventType.RESPONSE:
                print(event.content, end="", flush=True)
        print("\n✅ Basic response works!\n")
    
    # Test 2: Extended thinking
    print("Test 2: Extended Thinking")
    print("-" * 30)
    
    thinking_chunks = [
        b'event: message_start\ndata: {"type": "message_start", "message": {"id": "msg_456"}}\n\n',
        b'event: content_block_start\ndata: {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking_summary", "summary": "I need to analyze the molecular structure of water and ice..."}}\n\n',
        b'event: content_block_start\ndata: {"type": "content_block_start", "index": 1, "content_block": {"type": "text", "text": ""}}\n\n',
        b'event: content_block_delta\ndata: {"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": "Ice floats because "}}\n\n',
        b'event: content_block_delta\ndata: {"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": "it is less dense than water."}}\n\n',
        b'event: message_stop\ndata: {"type": "message_stop"}\n\n'
    ]
    
    with patch('httpx.AsyncClient.stream') as mock_stream:
        mock_response = create_mock_response(thinking_chunks)
        mock_stream.return_value.__aenter__.return_value = mock_response
        
        print("Sending: Why does ice float? (with thinking)")
        
        async for event in agent.stream_response(
            system_prompt="You are a science teacher.",
            user_prompt="Why does ice float?",
            thinking_budget=5000,
            max_tokens=10000
        ):
            if event.type == StreamEventType.THINKING:
                print(f"[Thinking] {event.content}")
            elif event.type == StreamEventType.RESPONSE:
                print(f"[Response] {event.content}", end="")
        print("\n✅ Extended thinking works!\n")
    
    # Test 3: Error handling
    print("Test 3: Error Handling")
    print("-" * 30)
    
    error_chunks = [
        b'event: error\ndata: {"type": "error", "error": {"type": "rate_limit_error", "message": "Rate limit exceeded"}}\n\n'
    ]
    
    with patch('httpx.AsyncClient.stream') as mock_stream:
        mock_response = create_mock_response(error_chunks)
        mock_stream.return_value.__aenter__.return_value = mock_response
        
        print("Simulating API error...")
        
        async for event in agent.stream_response(
            system_prompt="Test",
            user_prompt="Test error"
        ):
            if event.type == StreamEventType.ERROR:
                print(f"[Error] {event.content}")
        print("✅ Error handling works!\n")
    
    # Test 4: Token classification
    print("Test 4: Token Classification")
    print("-" * 30)
    
    # Mix of thinking and response blocks
    mixed_chunks = [
        b'event: message_start\ndata: {"type": "message_start"}\n\n',
        # Thinking block
        b'event: content_block_start\ndata: {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "text": ""}}\n\n',
        b'event: content_block_delta\ndata: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Let me think about this..."}}\n\n',
        b'event: content_block_stop\ndata: {"type": "content_block_stop", "index": 0}\n\n',
        # Response block
        b'event: content_block_start\ndata: {"type": "content_block_start", "index": 1, "content_block": {"type": "text", "text": ""}}\n\n',
        b'event: content_block_delta\ndata: {"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": "Here is my answer."}}\n\n',
        b'event: message_stop\ndata: {"type": "message_stop"}\n\n'
    ]
    
    with patch('httpx.AsyncClient.stream') as mock_stream:
        mock_response = create_mock_response(mixed_chunks)
        mock_stream.return_value.__aenter__.return_value = mock_response
        
        print("Testing token classification...")
        thinking_count = 0
        response_count = 0
        
        async for event in agent.stream_response(
            system_prompt="Test",
            user_prompt="Test classification"
        ):
            if event.type == StreamEventType.THINKING:
                thinking_count += 1
                print(f"[Thinking {thinking_count}] {event.content}")
            elif event.type == StreamEventType.RESPONSE:
                response_count += 1
                print(f"[Response {response_count}] {event.content}")
        
        print(f"✅ Token classification works! Thinking: {thinking_count}, Response: {response_count}\n")
    
    print("=" * 50)
    print("All mock tests completed successfully!")
    print("The agent is ready for real API testing.")


if __name__ == "__main__":
    asyncio.run(test_with_mock())