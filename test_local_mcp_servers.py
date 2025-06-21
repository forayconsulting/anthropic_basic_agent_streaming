#!/usr/bin/env python3
"""Test MCP connection with local servers (safe version)."""

import asyncio
import json
import os
from pathlib import Path
from claude_agent.mcp_client_real import RealMCPClient


def mask_sensitive_value(key: str, value: str) -> str:
    """Mask sensitive values in environment variables."""
    sensitive_keys = ['token', 'secret', 'key', 'password', 'api']
    if any(s in key.lower() for s in sensitive_keys):
        if len(value) > 8:
            return value[:4] + '***' + value[-4:]
        else:
            return '***'
    return value


async def test_server_safe(name: str, config: dict):
    """Test a server with masked sensitive data."""
    print(f"\nTesting MCP Server: {name}")
    print("=" * 60)
    
    client = RealMCPClient()
    
    try:
        # Extract and mask sensitive data
        command = config['command']
        args = config.get('args', [])
        env = config.get('env', {})
        
        # Display configuration (with masked env vars)
        print(f"Command: {command}")
        print(f"Args: {args}")
        if env:
            print("Environment variables:")
            for k, v in env.items():
                masked_value = mask_sensitive_value(k, v)
                print(f"  {k}: {masked_value}")
        
        # Connect
        print("\nConnecting...")
        await client.connect_stdio(command=command, args=args, env=env)
        print("✓ Connected!")
        
        # Get capabilities
        tools = await client.list_tools()
        resources = await client.list_resources()
        
        print(f"\nCapabilities:")
        print(f"  Tools: {len(tools)}")
        print(f"  Resources: {len(resources)}")
        
        # Show first few tools
        if tools:
            print(f"\nSample tools:")
            for tool in tools[:3]:
                print(f"  - {tool.name}: {tool.description[:60]}...")
        
        # Show first few resources
        if resources:
            print(f"\nSample resources:")
            for resource in resources[:3]:
                print(f"  - {resource.name}: {resource.description[:60]}...")
        
        print("\n✅ Server test successful!")
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
    
    finally:
        await client.disconnect()
        print("✓ Disconnected")


async def main():
    """Test all configured MCP servers."""
    print("MCP Server Connection Tests")
    print("=" * 60)
    
    # Load config
    config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    
    if not config_path.exists():
        print(f"Config not found at: {config_path}")
        return
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    servers = config.get('mcpServers', {})
    print(f"\nFound {len(servers)} MCP servers:")
    for name in servers:
        print(f"  - {name}")
    
    # Test each server
    print("\nStarting tests...")
    print("=" * 60)
    
    # Start with filesystem server (usually safest)
    if 'filesystem' in servers:
        await test_server_safe('filesystem', servers['filesystem'])
    
    # Test only filesystem by default (safest option)
    print("\n\nTo test other servers, run with --all flag")
    
    import sys
    if '--all' in sys.argv:
        for name, server_config in servers.items():
            if name != 'filesystem':  # Skip filesystem since we already tested it
                await test_server_safe(name, server_config)
                print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())