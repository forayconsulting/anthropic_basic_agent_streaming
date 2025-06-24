#!/usr/bin/env python3
"""Test MCP connection directly with the valid token."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.claude_agent.mcp_client import MCPClientWrapper


async def test_direct_connection():
    """Test MCP connection with known valid token."""
    
    print("Testing direct MCP connection with valid GitHub token\n")
    
    # The token we verified is valid
    token = "your_github_token_here"
    
    client = MCPClientWrapper()
    
    try:
        print("1. Connecting to GitHub MCP server...")
        print(f"   Token: {token[:10]}...{token[-4:]}")
        
        await client.connect_stdio(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": token}
        )
        
        print("   ✅ Connection established")
        
        # Wait for initialization
        print("\n2. Waiting for server initialization...")
        for i in range(5):
            await asyncio.sleep(1)
            print(f"   Waited {i+1} seconds...")
            
            # Try to list tools
            try:
                tools = await client.list_tools()
                if tools:
                    print(f"   ✅ Found {len(tools)} tools!")
                    break
            except Exception as e:
                print(f"   Still waiting... ({e})")
        
        # Final check
        print("\n3. Final tool check...")
        tools = await client.list_tools()
        resources = await client.list_resources()
        
        print(f"\nResults:")
        print(f"  Tools: {len(tools)}")
        print(f"  Resources: {len(resources)}")
        
        if tools:
            print("\nAvailable tools:")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
        else:
            print("\n⚠️  No tools found despite valid token!")
            
        # Get context
        context = await client.get_context()
        print(f"\nContext: {context}")
        
        await client.disconnect()
        print("\n✅ Test completed")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_env_passing():
    """Test that environment variables are passed correctly."""
    
    print("\n\nTesting environment variable passing\n")
    
    import subprocess
    
    # Test 1: Direct subprocess call
    print("1. Testing direct subprocess with env var...")
    
    env = os.environ.copy()
    env["TEST_VAR"] = "test_value"
    
    try:
        result = subprocess.run(
            ["npx", "-y", "@modelcontextprotocol/server-github", "--help"],
            env=env,
            capture_output=True,
            text=True,
            timeout=10
        )
        print(f"   Exit code: {result.returncode}")
        if result.stdout:
            print(f"   Output preview: {result.stdout[:200]}...")
        if result.stderr:
            print(f"   Error: {result.stderr[:200]}...")
    except Exception as e:
        print(f"   Error: {e}")


if __name__ == "__main__":
    print("=== Direct MCP Connection Test ===\n")
    asyncio.run(test_direct_connection())
    asyncio.run(test_env_passing())