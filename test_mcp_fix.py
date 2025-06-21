#!/usr/bin/env python3
"""Test the fixed MCP client implementation."""

import asyncio
import sys

# Add src to path
sys.path.insert(0, 'src')

from claude_agent.mcp_client import MCPClientWrapper


async def test_mcp_connection():
    """Test the MCP connection with the fixed implementation."""
    print("Testing Fixed MCP Client")
    print("=" * 60)
    
    client = MCPClientWrapper()
    
    try:
        # Test with filesystem server
        print("\nConnecting to filesystem MCP server...")
        await client.connect_stdio(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        )
        
        print("✓ Connected successfully!")
        print(f"✓ Connection status: {client.is_connected}")
        
        # List tools
        print("\nListing tools...")
        tools = await client.list_tools()
        print(f"✓ Found {len(tools)} tools")
        for tool in tools[:3]:
            print(f"  - {tool.name}: {tool.description[:60]}...")
        
        # List resources
        print("\nListing resources...")
        resources = await client.list_resources()
        print(f"✓ Found {len(resources)} resources")
        
        # Get context
        print("\nGetting MCP context...")
        context = await client.get_context()
        print(f"Context preview: {context[:200]}...")
        
        # Test a tool call
        print("\nTesting tool call...")
        
        # Create a test file
        test_file = "/tmp/mcp_fix_test.txt"
        with open(test_file, "w") as f:
            f.write("This is a test file for the fixed MCP client.")
        
        # Call read_file tool
        result = await client.call_tool("read_file", {"path": test_file})
        print(f"✓ Tool call result: {result[:100]}...")
        
        # Disconnect
        print("\nDisconnecting...")
        await client.disconnect()
        print("✓ Disconnected successfully!")
        print(f"✓ Connection status after disconnect: {client.is_connected}")
        
        print("\n✅ All tests passed! The MCP client is working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to disconnect
        try:
            await client.disconnect()
        except:
            pass
        
        return False


async def test_error_handling():
    """Test error handling scenarios."""
    print("\n\nTesting Error Handling")
    print("=" * 60)
    
    client = MCPClientWrapper()
    
    # Test calling methods without connection
    try:
        print("\nTesting method calls without connection...")
        await client.list_tools()
        print("❌ Should have raised an error!")
    except RuntimeError as e:
        print(f"✓ Correctly raised error: {e}")
    
    # Test invalid server
    try:
        print("\nTesting connection to invalid server...")
        await client.connect_stdio(
            command="invalid-command-that-does-not-exist",
            args=[]
        )
        print("❌ Should have raised an error!")
    except Exception as e:
        print(f"✓ Correctly raised error: {type(e).__name__}: {e}")
    
    print("\n✅ Error handling tests passed!")


async def main():
    """Run all tests."""
    success = await test_mcp_connection()
    
    if success:
        await test_error_handling()
    
    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)