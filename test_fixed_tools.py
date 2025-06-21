#!/usr/bin/env python3
"""Test the fixed tool integration."""

import asyncio
import json
import os
from pathlib import Path
from claude_agent.agent_tools_fixed import ClaudeAgentWithToolsFixed, StreamEventType


async def test_fixed_integration():
    """Test the fixed tool integration."""
    print("Fixed Tool Integration Test")
    print("=" * 60)
    
    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Please set ANTHROPIC_API_KEY environment variable")
        return
    
    # Create test files
    test_dir = "/tmp/mcp_fixed_test"
    os.makedirs(test_dir, exist_ok=True)
    
    with open(f"{test_dir}/data.json", "w") as f:
        json.dump({
            "test": "success",
            "items": [1, 2, 3],
            "message": "Tool integration is working!"
        }, f, indent=2)
    
    with open(f"{test_dir}/readme.txt", "w") as f:
        f.write("This is a test file for the fixed MCP integration.\n")
        f.write("If Claude can read this, the tools are working correctly.")
    
    print(f"Created test files in {test_dir}")
    
    # Create agent
    agent = ClaudeAgentWithToolsFixed(api_key=api_key)
    
    try:
        # Connect to filesystem server
        print("\nConnecting to filesystem MCP server...")
        await agent.connect_mcp(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", test_dir]
        )
        print("✓ Connected!")
        
        # Wait for initialization
        await asyncio.sleep(2)
        
        # Check tools
        tools = agent.mcp_manager.tools
        print(f"\nAvailable tools: {len(tools)}")
        for tool in tools[:3]:
            print(f"  - {tool.name}")
        
        # Test 1: Simple file read
        print("\n\nTest 1: Reading a specific file")
        print("-" * 60)
        
        events = []
        async for event in agent.stream_response_with_tools(
            system_prompt="You are a helpful assistant with filesystem access. Use your tools to answer questions about files.",
            user_prompt=f"What's in the data.json file in {test_dir}? Read it and tell me what the 'message' field says."
        ):
            events.append(event)
            if event.type == StreamEventType.RESPONSE:
                print(event.content, end="", flush=True)
            elif event.type == StreamEventType.TOOL_USE:
                print(f"\n🔧 {event.content}")
            elif event.type == StreamEventType.TOOL_RESULT:
                print(f"\n✓ Tool executed: {event.metadata.get('tool_name')}")
        
        # Analyze events
        print(f"\n\nEvent Analysis:")
        event_counts = {}
        for event in events:
            event_counts[event.type.value] = event_counts.get(event.type.value, 0) + 1
        
        for event_type, count in event_counts.items():
            print(f"  {event_type}: {count}")
        
        # Check if tools were used
        tool_used = any(e.type == StreamEventType.TOOL_USE for e in events)
        print(f"\n{'✅' if tool_used else '❌'} Tools were {'used' if tool_used else 'NOT used'}")
        
        # Test 2: Multiple operations
        print("\n\nTest 2: Multiple file operations")
        print("-" * 60)
        
        async for event in agent.stream_response_with_tools(
            system_prompt="You are a helpful assistant with filesystem tools.",
            user_prompt=f"In {test_dir}, list all files, read the readme.txt file, and tell me how many items are in the 'items' array in data.json"
        ):
            if event.type == StreamEventType.RESPONSE:
                print(event.content, end="", flush=True)
            elif event.type == StreamEventType.TOOL_USE:
                print(f"\n🔧 {event.content}")
            elif event.type == StreamEventType.TOOL_RESULT:
                metadata = event.metadata
                print(f"\n✓ {metadata.get('tool_name')} completed")
        
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\nDisconnecting...")
        await agent.disconnect_mcp()
        print("✓ Disconnected")
        
        # Cleanup
        import shutil
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print(f"✓ Cleaned up {test_dir}")


async def main():
    """Run the test."""
    await test_fixed_integration()


if __name__ == "__main__":
    # Set API key if provided
    import sys
    if len(sys.argv) > 1:
        os.environ["ANTHROPIC_API_KEY"] = sys.argv[1]
    
    asyncio.run(main())