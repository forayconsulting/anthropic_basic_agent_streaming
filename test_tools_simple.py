#!/usr/bin/env python3
"""Simple test of tool integration with existing files."""

import asyncio
import os
from claude_agent.agent_tools_fixed import ClaudeAgentWithToolsFixed, StreamEventType


async def simple_tool_test():
    """Simple test with existing tmp directory."""
    print("Simple Tool Integration Test")
    print("=" * 60)
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Please set ANTHROPIC_API_KEY")
        return
    
    # Create a simple test file
    test_file = "/tmp/simple_test.txt"
    with open(test_file, "w") as f:
        f.write("Hello from MCP Tool Integration!\n")
        f.write("This proves that Claude can use MCP tools.\n")
        f.write("The integration is working correctly.")
    
    print(f"Created test file: {test_file}")
    
    agent = ClaudeAgentWithToolsFixed(api_key=api_key)
    
    try:
        # Connect to filesystem server with /tmp access
        print("\nConnecting to MCP server...")
        await agent.connect_mcp(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        )
        print("✓ Connected!")
        
        await asyncio.sleep(2)
        
        # Simple test
        print("\n\nAsking Claude to read our file...")
        print("-" * 60)
        
        tool_uses = 0
        responses = 0
        
        async for event in agent.stream_response_with_tools(
            system_prompt="You are a helpful assistant with filesystem tools.",
            user_prompt=f"Please read the file {test_file} and tell me what it says."
        ):
            if event.type == StreamEventType.RESPONSE:
                print(event.content, end="", flush=True)
                responses += 1
            elif event.type == StreamEventType.TOOL_USE:
                print(f"\n🔧 {event.content}")
                tool_uses += 1
            elif event.type == StreamEventType.TOOL_RESULT:
                print(f"✅ Tool completed")
        
        print(f"\n\nResults:")
        print(f"  Tool uses: {tool_uses}")
        print(f"  Response chunks: {responses}")
        print(f"  Success: {'✅ Yes' if tool_uses > 0 else '❌ No'}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await agent.disconnect_mcp()
        if os.path.exists(test_file):
            os.remove(test_file)
        print("\n✓ Cleanup complete")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        os.environ["ANTHROPIC_API_KEY"] = sys.argv[1]
    
    asyncio.run(simple_tool_test())