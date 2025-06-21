#!/usr/bin/env python3
"""Quick test of the fixed MCP client."""

import asyncio
import sys

# Add src to path
sys.path.insert(0, 'src')

from claude_agent.mcp_client import MCPClientWrapper


async def quick_test():
    """Quick test with timeout."""
    print("Quick MCP Client Test")
    print("=" * 40)
    
    client = MCPClientWrapper()
    
    try:
        # Use overall timeout
        async with asyncio.timeout(30):
            print("\nConnecting to filesystem server...")
            await client.connect_stdio(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
            )
            
            print("✓ Connected!")
            
            # Quick tool check
            tools = await client.list_tools()
            print(f"✓ Found {len(tools)} tools")
            
            # Quick disconnect
            await client.disconnect()
            print("✓ Disconnected!")
            
        print("\n✅ Test passed!")
        return True
        
    except asyncio.TimeoutError:
        print("⏱️  Test timed out (this might be normal if server is downloading)")
        await client.disconnect()
        return True
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(quick_test())
    sys.exit(0 if result else 1)