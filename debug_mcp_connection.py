#!/usr/bin/env python3
"""Debug MCP connection issues."""

import asyncio
import subprocess
import sys


async def test_npx_command():
    """Test if npx command works."""
    print("Testing npx command directly...")
    
    try:
        # Test npx version
        result = subprocess.run(["npx", "--version"], capture_output=True, text=True)
        print(f"npx version: {result.stdout.strip()}")
        
        # Test running MCP server directly
        print("\nTesting MCP server startup (5 second timeout)...")
        proc = await asyncio.create_subprocess_exec(
            "npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            # Wait for initial output
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
        except asyncio.TimeoutError:
            print("Server is running (timed out waiting for completion)")
            proc.terminate()
            await proc.wait()
            
    except Exception as e:
        print(f"Error: {e}")


async def test_mcp_handshake():
    """Test MCP handshake."""
    print("\n\nTesting MCP handshake...")
    
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        
        # Simple server parameters
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        )
        
        print("Creating stdio client...")
        
        # Use timeout for the connection
        async with asyncio.timeout(10):
            async with stdio_client(server_params) as (read_stream, write_stream):
                print("✓ Stdio streams created")
                
                # Create session
                session = ClientSession(read_stream, write_stream)
                print("✓ Session created")
                
                # Initialize with timeout
                print("Initializing session (this may take a moment)...")
                await asyncio.wait_for(session.initialize(), timeout=10.0)
                print("✓ Session initialized!")
                
                # Quick tool check
                result = await session.list_tools()
                print(f"✓ Found {len(result.tools)} tools")
                
                # Close session
                await session.close()
                print("✓ Session closed")
                
    except asyncio.TimeoutError:
        print("❌ Timeout during MCP connection")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run debug tests."""
    print("MCP Connection Debugging")
    print("=" * 60)
    
    await test_npx_command()
    await test_mcp_handshake()


if __name__ == "__main__":
    asyncio.run(main())