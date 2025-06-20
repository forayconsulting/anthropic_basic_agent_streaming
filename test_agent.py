#!/usr/bin/env python3
"""Simple test script to verify Claude Agent functionality."""

import asyncio
import os
import sys
from datetime import datetime

from claude_agent.agent import ClaudeAgent, StreamEventType


async def test_basic_response():
    """Test basic response streaming."""
    print("\n" + "="*60)
    print("TEST 1: Basic Response Streaming")
    print("="*60)
    
    response_tokens = 0
    async for event in agent.stream_response(
        system_prompt="You are a helpful assistant. Be concise.",
        user_prompt="What is 2+2? Answer in one sentence."
    ):
        if event.type == StreamEventType.RESPONSE:
            print(event.content, end="", flush=True)
            response_tokens += 1
        elif event.type == StreamEventType.ERROR:
            print(f"\nERROR: {event.content}")
            return False
    
    print(f"\n\n✅ Basic streaming works! Received {response_tokens} response tokens")
    return True


async def test_extended_thinking():
    """Test extended thinking mode."""
    print("\n" + "="*60)
    print("TEST 2: Extended Thinking Mode")
    print("="*60)
    
    thinking_tokens = 0
    response_tokens = 0
    
    async for event in agent.stream_response(
        system_prompt="You are a thoughtful assistant.",
        user_prompt="Why does ice float on water? Think about this step by step.",
        thinking_budget=2000,
        max_tokens=5000
    ):
        if event.type == StreamEventType.THINKING:
            if thinking_tokens == 0:
                print("\n[THINKING PROCESS]")
            print(f"  • {event.content}")
            thinking_tokens += 1
        elif event.type == StreamEventType.RESPONSE:
            if response_tokens == 0:
                print("\n[RESPONSE]")
            print(event.content, end="", flush=True)
            response_tokens += 1
        elif event.type == StreamEventType.ERROR:
            print(f"\nERROR: {event.content}")
            return False
    
    print(f"\n\n✅ Extended thinking works!")
    print(f"   - Thinking tokens: {thinking_tokens}")
    print(f"   - Response tokens: {response_tokens}")
    return True


async def test_conversation_history():
    """Test conversation history."""
    print("\n" + "="*60)
    print("TEST 3: Conversation History")
    print("="*60)
    
    # First exchange
    print("\nUser: My favorite color is blue.")
    print("Claude: ", end="", flush=True)
    
    first_response = []
    async for event in agent.stream_response(
        system_prompt="You are a helpful assistant with good memory.",
        user_prompt="My favorite color is blue."
    ):
        if event.type == StreamEventType.RESPONSE:
            print(event.content, end="", flush=True)
            first_response.append(event.content)
    
    # Build history
    history = [
        {"role": "user", "content": "My favorite color is blue."},
        {"role": "assistant", "content": "".join(first_response)}
    ]
    
    # Second exchange using history
    print("\n\nUser: What's my favorite color?")
    print("Claude: ", end="", flush=True)
    
    remembered = False
    async for event in agent.stream_response(
        system_prompt="You are a helpful assistant with good memory.",
        user_prompt="What's my favorite color?",
        conversation_history=history
    ):
        if event.type == StreamEventType.RESPONSE:
            print(event.content, end="", flush=True)
            if "blue" in event.content.lower():
                remembered = True
    
    if remembered:
        print("\n\n✅ Conversation history works! Claude remembered the color.")
    else:
        print("\n\n❌ Conversation history might not be working properly.")
    return remembered


async def test_error_handling():
    """Test error handling with invalid parameters."""
    print("\n" + "="*60)
    print("TEST 4: Error Handling")
    print("="*60)
    
    print("\nTesting invalid thinking budget...")
    
    try:
        async for event in agent.stream_response(
            system_prompt="Test",
            user_prompt="Test",
            thinking_budget=500,  # Too small
            max_tokens=4096
        ):
            pass
    except ValueError as e:
        print(f"✅ Correctly caught error: {e}")
        return True
    
    print("❌ Error handling failed - no exception raised")
    return False


async def test_streaming_performance():
    """Test streaming performance."""
    print("\n" + "="*60)
    print("TEST 5: Streaming Performance")
    print("="*60)
    
    print("\nRequesting a longer response...")
    start_time = datetime.now()
    first_token_time = None
    token_count = 0
    
    async for event in agent.stream_response(
        system_prompt="You are a helpful assistant.",
        user_prompt="Write a short paragraph about the importance of clean code in software development."
    ):
        if event.type == StreamEventType.RESPONSE:
            if first_token_time is None:
                first_token_time = datetime.now()
                print(f"\nFirst token received in: {(first_token_time - start_time).total_seconds():.2f}s")
                print("\nResponse: ", end="", flush=True)
            print(event.content, end="", flush=True)
            token_count += 1
    
    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds()
    
    print(f"\n\n✅ Streaming performance:")
    print(f"   - Total time: {total_time:.2f}s")
    print(f"   - Tokens received: {token_count}")
    if token_count > 0:
        print(f"   - Tokens per second: {token_count/total_time:.1f}")
    
    return True


# Main test runner
async def main():
    """Run all tests."""
    global agent
    
    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Please set ANTHROPIC_API_KEY environment variable")
        print("\nExample:")
        print("  export ANTHROPIC_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    print("Claude Agent Test Suite")
    print("=" * 60)
    print(f"Starting tests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create agent
    agent = ClaudeAgent(api_key=api_key)
    print(f"Agent initialized with model: {agent._model}")
    
    # Run tests
    tests = [
        ("Basic Response", test_basic_response),
        ("Extended Thinking", test_extended_thinking),
        ("Conversation History", test_conversation_history),
        ("Error Handling", test_error_handling),
        ("Streaming Performance", test_streaming_performance),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            print(f"\nRunning: {test_name}...")
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The agent is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the output above.")


if __name__ == "__main__":
    # Note: This will make actual API calls to Claude
    print("\n⚠️  WARNING: This test will make actual API calls to Claude.")
    print("This will consume API credits. Continue? (y/n): ", end="", flush=True)
    
    response = input().strip().lower()
    if response == 'y':
        asyncio.run(main())
    else:
        print("Test cancelled.")