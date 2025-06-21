#!/usr/bin/env python3
"""Test MCP connection with a local server."""

import asyncio
import json
import os
from pathlib import Path
from claude_agent.mcp_client_real import RealMCPClient


async def test_mcp_server(server_config: dict):
    """Test connection to an MCP server."""
    print(f"\nTesting MCP Server: {server_config.get('name', 'Unknown')}")
    print("=" * 60)
    
    client = RealMCPClient()
    
    try:
        # Extract connection parameters
        command = server_config['command']
        args = server_config.get('args', [])
        env = server_config.get('env', {})
        
        print(f"Command: {command}")
        print(f"Args: {args}")
        print(f"Env: {env}")
        
        # Connect to server
        print("\nConnecting to server...")
        await client.connect_stdio(command=command, args=args, env=env)
        print("✓ Connected successfully!")
        
        # List tools
        print("\nListing tools...")
        tools = await client.list_tools()
        if tools:
            print(f"Found {len(tools)} tools:")
            for tool in tools[:5]:  # Show first 5 tools
                print(f"  - {tool.name}: {tool.description[:50]}...")
                if tool.input_schema:
                    print(f"    Schema: {json.dumps(tool.input_schema, indent=6)[:100]}...")
        else:
            print("No tools found.")
        
        # List resources
        print("\nListing resources...")
        resources = await client.list_resources()
        if resources:
            print(f"Found {len(resources)} resources:")
            for resource in resources[:5]:  # Show first 5 resources
                print(f"  - {resource.name} ({resource.uri}): {resource.description[:50]}...")
        else:
            print("No resources found.")
        
        # Get context
        print("\nGetting context...")
        context = await client.get_context()
        print(f"Context preview:\n{context[:500]}...")
        
        # Test a simple tool call if available
        if tools and any(tool.name == "echo" for tool in tools):
            print("\nTesting echo tool...")
            result = await client.call_tool("echo", {"message": "Hello from MCP test!"})
            print(f"Echo result: {result}")
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Disconnect
        print("\nDisconnecting...")
        await client.disconnect()
        print("✓ Disconnected")


async def find_claude_config():
    """Find Claude Desktop configuration to locate MCP servers."""
    config_paths = [
        Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
        Path.home() / ".claude" / "claude_desktop_config.json",
        Path.home() / ".config" / "claude" / "claude_desktop_config.json",
    ]
    
    for path in config_paths:
        if path.exists():
            print(f"Found Claude config at: {path}")
            with open(path, 'r') as f:
                return json.load(f)
    
    return None


async def main():
    """Main test function."""
    print("MCP Connection Test")
    print("=" * 60)
    
    # Try to find Claude Desktop config
    config = await find_claude_config()
    
    if config and "mcpServers" in config:
        servers = config["mcpServers"]
        print(f"\nFound {len(servers)} MCP servers in Claude config:")
        for name, server_config in servers.items():
            print(f"  - {name}")
        
        # Test each server
        for name, server_config in servers.items():
            server_config['name'] = name
            await test_mcp_server(server_config)
            print("\n" + "=" * 60)
    else:
        # Manual test configuration
        print("\nNo Claude config found. Testing with example server...")
        
        # Example: filesystem MCP server
        example_server = {
            "name": "filesystem",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            "env": {}
        }
        
        await test_mcp_server(example_server)


if __name__ == "__main__":
    asyncio.run(main())