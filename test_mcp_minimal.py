#!/usr/bin/env python3
"""Minimal test of MCP connection to isolate the issue."""

import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_minimal():
    """Test minimal MCP connection."""
    print("Testing minimal MCP connection...\n")
    
    # Token that we know is valid
    token = "your_github_token_here"
    
    # Prepare environment
    env = os.environ.copy()
    env["GITHUB_PERSONAL_ACCESS_TOKEN"] = token
    
    # Server parameters
    params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env=env
    )
    
    print("1. Starting MCP server...")
    
    try:
        # Use the context manager properly
        async with stdio_client(params) as (read_stream, write_stream):
            print("2. Stdio connection established")
            
            # Create session
            async with ClientSession(read_stream, write_stream) as session:
                print("3. Session created")
                
                # Initialize
                await session.initialize()
                print("4. Session initialized")
                
                # List tools
                print("5. Listing tools...")
                result = await session.list_tools()
                
                tools = result.tools if hasattr(result, 'tools') else []
                print(f"6. Found {len(tools)} tools")
                
                if tools:
                    print("\nAvailable tools:")
                    for tool in tools[:5]:  # First 5
                        print(f"  - {tool.name}: {getattr(tool, 'description', 'No description')}")
                else:
                    print("\n⚠️  No tools found!")
                    print("   This might mean:")
                    print("   - The server needs more time to initialize")
                    print("   - The token is not being passed correctly")
                    print("   - The server has an issue")
                
                # Try resources too
                print("\n7. Listing resources...")
                res_result = await session.list_resources()
                resources = res_result.resources if hasattr(res_result, 'resources') else []
                print(f"8. Found {len(resources)} resources")
                
        print("\n✅ Test completed successfully")
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=== Minimal MCP Test ===\n")
    asyncio.run(test_minimal())