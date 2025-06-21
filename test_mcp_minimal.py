#!/usr/bin/env python3
"""Minimal MCP connection test."""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_minimal():
    """Test minimal MCP connection."""
    print("Testing minimal MCP connection...")
    
    # Simple echo server test
    server_params = StdioServerParameters(
        command="echo",
        args=["Hello MCP"]
    )
    
    try:
        print("Creating stdio client...")
        async with asyncio.timeout(5):
            async with stdio_client(server_params) as (read_stream, write_stream):
                print("✓ Stdio client created")
                # The echo command will exit immediately, so this should complete
    except asyncio.TimeoutError:
        print("❌ Timeout creating stdio client")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
    
    # Test with a real MCP server that should respond
    print("\n\nTesting with filesystem server...")
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    )
    
    try:
        print("Creating stdio client (10s timeout)...")
        async with asyncio.timeout(10):
            async with stdio_client(server_params) as (read_stream, write_stream):
                print("✓ Stdio client created")
                
                # Create session
                session = ClientSession(read_stream, write_stream)
                print("✓ Session created")
                
                # Try to initialize
                print("Initializing session...")
                await session.initialize()
                print("✓ Session initialized!")
                
                # Quick check
                result = await session.list_tools()
                print(f"✓ Found {len(result.tools)} tools!")
                
                await session.close()
                
    except asyncio.TimeoutError:
        print("❌ Timeout (server may be downloading dependencies)")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_minimal())