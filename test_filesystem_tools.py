#!/usr/bin/env python3
"""Test Filesystem MCP server with tool integration."""

import asyncio
import json
import os
from pathlib import Path
from claude_agent.agent_with_tools import ClaudeAgentWithTools, StreamEventType


async def test_filesystem_with_tools():
    """Test filesystem server with full tool integration."""
    print("Filesystem MCP Server Test - Full Tool Integration")
    print("=" * 60)
    
    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Please set ANTHROPIC_API_KEY environment variable")
        return
    
    # Create test files
    test_dir = "/tmp/mcp_test"
    os.makedirs(test_dir, exist_ok=True)
    
    # Create some test files
    with open(f"{test_dir}/readme.txt", "w") as f:
        f.write("This is a test directory for MCP integration.\n")
        f.write("It contains several files to demonstrate tool usage.\n")
    
    with open(f"{test_dir}/data.json", "w") as f:
        json.dump({"name": "Test Data", "value": 42, "items": ["a", "b", "c"]}, f, indent=2)
    
    with open(f"{test_dir}/script.py", "w") as f:
        f.write("#!/usr/bin/env python3\n")
        f.write("print('Hello from MCP test!')\n")
    
    print(f"Created test files in {test_dir}")
    
    # Load Claude config
    config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    with open(config_path) as f:
        config = json.load(f)
    
    # Get filesystem server config
    fs_config = config['mcpServers']['filesystem']
    
    # Create agent
    agent = ClaudeAgentWithTools(api_key=api_key)
    
    try:
        # Connect to filesystem server (but with our test directory)
        print("\nConnecting to filesystem MCP server...")
        await agent.connect_mcp(
            command=fs_config['command'],
            args=["-y", "@modelcontextprotocol/server-filesystem", test_dir]
        )
        print("✓ Connected!")
        
        # Wait for server to initialize
        await asyncio.sleep(2)
        
        # Check available tools
        tools = agent.mcp_manager.tools
        print(f"\nAvailable tools ({len(tools)}):")
        for tool in tools[:5]:  # Show first 5
            print(f"  - {tool.name}: {tool.description[:60]}...")
        
        # Test 1: List files
        print("\n\nTest 1: List files in directory")
        print("-" * 60)
        
        async for event in agent.stream_response_with_tools(
            system_prompt="You are a helpful assistant with filesystem access.",
            user_prompt=f"What files are in the {test_dir} directory? List them with their types."
        ):
            if event.type == StreamEventType.RESPONSE:
                print(event.content, end="", flush=True)
            elif event.type == StreamEventType.TOOL_USE:
                print(f"\n[Tool: {event.content}]", end="")
            elif event.type == StreamEventType.TOOL_RESULT:
                # Don't print full result as it might be long
                pass
        
        # Test 2: Read specific file
        print("\n\n\nTest 2: Read and analyze file")
        print("-" * 60)
        
        async for event in agent.stream_response_with_tools(
            system_prompt="You are a helpful assistant with filesystem access.",
            user_prompt=f"Read the data.json file in {test_dir} and tell me what it contains."
        ):
            if event.type == StreamEventType.RESPONSE:
                print(event.content, end="", flush=True)
            elif event.type == StreamEventType.TOOL_USE:
                print(f"\n[Tool: {event.content}]", end="")
        
        # Test 3: Multiple tool uses
        print("\n\n\nTest 3: Complex task with multiple tools")
        print("-" * 60)
        
        async for event in agent.stream_response_with_tools(
            system_prompt="You are a helpful assistant with filesystem access.",
            user_prompt=f"In {test_dir}, read all the files and give me a summary of what each file contains. Also tell me the total size of all files combined."
        ):
            if event.type == StreamEventType.RESPONSE:
                print(event.content, end="", flush=True)
            elif event.type == StreamEventType.TOOL_USE:
                print(f"\n[Tool: {event.content}]", end="")
        
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


async def test_direct_filesystem_connection():
    """Test direct filesystem MCP connection."""
    print("Direct Filesystem MCP Connection Test")
    print("=" * 60)
    
    from claude_agent.mcp_client_fixed import FixedMCPClient
    
    client = FixedMCPClient()
    
    try:
        print("Connecting to filesystem server...")
        async with client.connect(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        ) as session:
            print("✓ Connected!")
            
            # List tools
            print(f"\nTools: {len(client.tools)}")
            for tool in client.tools[:3]:
                print(f"  - {tool.name}")
            
            # List resources
            print(f"\nResources: {len(client.resources)}")
            
            # Try to read a directory
            if any(t.name == "list_directory" for t in client.tools):
                print("\nListing /tmp directory...")
                result = await session.call_tool("list_directory", {"path": "/tmp"})
                print("✓ Tool executed successfully")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run tests."""
    print("Filesystem MCP Tool Integration Tests")
    print("=" * 60)
    
    # Test direct connection first
    print("\n")
    await test_direct_filesystem_connection()
    
    # Then test with Claude
    print("\n\n" + "=" * 60 + "\n")
    await test_filesystem_with_tools()


if __name__ == "__main__":
    # Set API key if provided
    import sys
    if len(sys.argv) > 1:
        os.environ["ANTHROPIC_API_KEY"] = sys.argv[1]
    
    asyncio.run(main())