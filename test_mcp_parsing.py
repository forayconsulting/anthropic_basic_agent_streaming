#!/usr/bin/env python3
"""Test MCP command parsing and connection."""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.claude_agent.mcp_client import MCPClientWrapper
from src.claude_agent.agent import ClaudeAgent


async def test_mcp_parsing():
    """Test different MCP command formats."""
    
    print("Testing MCP command parsing...")
    
    # Test 1: Basic command without env vars
    print("\n1. Testing basic command (npx -y @modelcontextprotocol/server-github)")
    client1 = MCPClientWrapper()
    try:
        await client1.connect_stdio(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env=None
        )
        tools = await client1.list_tools()
        print(f"   ✓ Connected successfully, found {len(tools)} tools")
        await client1.disconnect()
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # Test 2: Command with environment variables (correct way)
    print("\n2. Testing command with env vars (proper method)")
    client2 = MCPClientWrapper()
    
    # Get token from environment or use test token
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "ghp_test_token")
    
    try:
        await client2.connect_stdio(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": token}
        )
        tools = await client2.list_tools()
        print(f"   ✓ Connected successfully, found {len(tools)} tools")
        
        # List available tools
        print("   Available tools:")
        for tool in tools[:5]:  # Show first 5 tools
            print(f"     - {tool.name}: {tool.description[:60]}...")
            
        await client2.disconnect()
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # Test 3: Show what's wrong with the current parsing
    print("\n3. Demonstrating current parsing issue")
    command_string = "npx -y @modelcontextprotocol/server-github -e GITHUB_PERSONAL_ACCESS_TOKEN=ghp_test"
    parts = command_string.split(' ')
    cmd = parts[0]
    args = parts[1:]
    
    print(f"   Input: {command_string}")
    print(f"   Current parsing:")
    print(f"     Command: {cmd}")
    print(f"     Args: {args}")
    print("   Problem: '-e' is not a valid npx argument, env vars need special handling")
    
    # Test 4: Proposed parsing solution
    print("\n4. Proposed parsing solution")
    print("   Option A: Use JSON format in the UI")
    print('   Example: {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"], "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "token"}}')
    
    print("\n   Option B: Use special syntax for env vars")
    print("   Example: ENV:GITHUB_PERSONAL_ACCESS_TOKEN=token npx -y @modelcontextprotocol/server-github")
    
    print("\n   Option C: Separate fields in UI for command, args, and env vars")


async def test_github_mcp_tools():
    """Test actual GitHub MCP server tools."""
    print("\n\nTesting GitHub MCP server with real token...")
    
    # Try to get token from environment
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not token:
        print("No GITHUB_PERSONAL_ACCESS_TOKEN found in environment")
        print("Skipping real GitHub MCP test")
        return
    
    client = MCPClientWrapper()
    try:
        print("Connecting to GitHub MCP server...")
        await client.connect_stdio(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": token}
        )
        
        # List tools
        tools = await client.list_tools()
        print(f"\nFound {len(tools)} tools:")
        for tool in tools:
            print(f"\n  {tool.name}:")
            print(f"    Description: {tool.description}")
            print(f"    Schema: {json.dumps(tool.input_schema, indent=6)}")
        
        # List resources
        resources = await client.list_resources()
        print(f"\nFound {len(resources)} resources:")
        for resource in resources[:5]:  # Show first 5
            print(f"  - {resource.name} ({resource.uri})")
        
        await client.disconnect()
        print("\nDisconnected successfully")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_mcp_parsing())
    asyncio.run(test_github_mcp_tools())