#!/usr/bin/env python3
"""Debug MCP GitHub connection issues."""

import asyncio
import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.claude_agent.mcp_client import MCPClientWrapper


async def test_github_mcp_debug():
    """Debug GitHub MCP connection with detailed logging."""
    
    print("=== MCP GitHub Debug Test ===\n")
    
    # Test 1: Check if npx and the package are available
    print("1. Checking npx availability...")
    try:
        result = subprocess.run(["npx", "--version"], capture_output=True, text=True)
        print(f"   npx version: {result.stdout.strip()}")
    except Exception as e:
        print(f"   ❌ npx not found: {e}")
        return
    
    # Test 2: Try different token formats
    tokens_to_test = [
        ("User provided token", "your_github_token_here"),
        ("Environment token", os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")),
    ]
    
    for token_name, token in tokens_to_test:
        if not token:
            print(f"\n2. Skipping {token_name} - not available")
            continue
            
        print(f"\n2. Testing with {token_name}")
        print(f"   Token preview: {token[:10]}...{token[-4:]}")
        
        client = MCPClientWrapper()
        
        try:
            # Connect with detailed logging
            print("\n   Connecting to GitHub MCP server...")
            await client.connect_stdio(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env={"GITHUB_PERSONAL_ACCESS_TOKEN": token}
            )
            
            print("   ✅ Connection established")
            
            # Give it a moment to fully initialize
            await asyncio.sleep(2)
            
            # Check tools
            print("\n   Checking tools...")
            tools = await client.list_tools()
            print(f"   Found {len(tools)} tools")
            
            if tools:
                print("\n   Available tools:")
                for tool in tools:
                    print(f"     - {tool.name}")
                    print(f"       Description: {tool.description}")
                    print(f"       Schema: {tool.input_schema}\n")
            else:
                print("   ⚠️  No tools found - this might indicate:")
                print("      - Invalid GitHub token")
                print("      - Token lacks necessary permissions")
                print("      - Server initialization issue")
            
            # Check resources
            print("\n   Checking resources...")
            resources = await client.list_resources()
            print(f"   Found {len(resources)} resources")
            
            if resources:
                print("\n   Available resources:")
                for res in resources[:5]:  # Show first 5
                    print(f"     - {res.name} ({res.uri})")
            
            await client.disconnect()
            print("\n   ✅ Disconnected successfully")
            
        except Exception as e:
            print(f"\n   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Test 3: Try without token to see behavior
    print("\n\n3. Testing without token (should fail or provide limited tools)")
    client = MCPClientWrapper()
    
    try:
        await client.connect_stdio(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={}  # No token
        )
        
        tools = await client.list_tools()
        print(f"   Without token: {len(tools)} tools available")
        
        if tools:
            print("   Tools available without auth:")
            for tool in tools:
                print(f"     - {tool.name}")
        
        await client.disconnect()
        
    except Exception as e:
        print(f"   Expected error without token: {e}")


async def test_simple_mcp_server():
    """Test with a simpler MCP server to verify basic functionality."""
    
    print("\n\n=== Testing Simple MCP Server ===")
    
    # Test with filesystem MCP server (doesn't need auth)
    print("\nTesting @modelcontextprotocol/server-filesystem...")
    
    client = MCPClientWrapper()
    
    try:
        await client.connect_stdio(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", os.path.expanduser("~")],
            env={}
        )
        
        tools = await client.list_tools()
        print(f"✅ Filesystem server provides {len(tools)} tools")
        
        if tools:
            print("Available tools:")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
        
        await client.disconnect()
        
    except Exception as e:
        print(f"❌ Error with filesystem server: {e}")


if __name__ == "__main__":
    print("Starting MCP GitHub debugging...\n")
    asyncio.run(test_github_mcp_debug())
    asyncio.run(test_simple_mcp_server())