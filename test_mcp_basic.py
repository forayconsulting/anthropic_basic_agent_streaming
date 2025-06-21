#!/usr/bin/env python3
"""Basic MCP connection test."""

import asyncio
import json
import sys
from pathlib import Path

# Import MCP SDK
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_basic_connection():
    """Test basic MCP connection."""
    print("Basic MCP Connection Test")
    print("=" * 60)
    
    # Load config
    config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    with open(config_path) as f:
        config = json.load(f)
    
    # Get filesystem server config
    fs_config = config['mcpServers']['filesystem']
    print(f"Server: filesystem")
    print(f"Command: {fs_config['command']}")
    print(f"Args: {fs_config['args']}")
    
    # Create server parameters
    server_params = StdioServerParameters(
        command=fs_config['command'],
        args=fs_config['args'],
        env=fs_config.get('env', {})
    )
    
    print("\nConnecting to server...")
    
    try:
        # Connect to server
        async with stdio_client(server_params) as (read_stream, write_stream):
            print("✓ Transport connected")
            
            # Create session
            session = ClientSession(read_stream, write_stream)
            
            # Initialize
            print("Initializing session...")
            await session.initialize()
            print("✓ Session initialized")
            
            # List tools
            print("\nFetching tools...")
            result = await session.list_tools()
            print(f"✓ Found {len(result.tools)} tools")
            
            # Show first few tools
            for i, tool in enumerate(result.tools[:3]):
                print(f"\n  Tool {i+1}: {tool.name}")
                print(f"    Description: {tool.description[:60]}...")
                
            # List resources
            print("\n\nFetching resources...")
            result = await session.list_resources()
            print(f"✓ Found {len(result.resources)} resources")
            
            # Test a simple tool call
            print("\n\nTesting tool call...")
            
            # Create test file
            test_file = "/tmp/mcp_test_basic.txt"
            with open(test_file, "w") as f:
                f.write("Basic MCP test content")
            
            # Call read_file tool
            print(f"Reading file: {test_file}")
            result = await session.call_tool("read_file", {"path": test_file})
            
            if hasattr(result, 'content') and result.content:
                print("✓ Tool call successful")
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(f"  Content: {content.text}")
            
            # Clean up
            print("\nClosing session...")
            await session.close()
            print("✓ Session closed")
            
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ Test completed successfully!")
    return True


async def main():
    """Run the test."""
    success = await test_basic_connection()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())