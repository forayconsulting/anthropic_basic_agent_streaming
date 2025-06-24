#!/usr/bin/env python3
"""Integration test for MCP connection with environment variables."""

import asyncio
import json
import os
import sys
import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_mcp_integration():
    """Test MCP connection through the chat server API."""
    
    base_url = "http://localhost:8080"
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return
    
    async with httpx.AsyncClient() as client:
        # Step 1: Create session
        print("1. Creating session...")
        response = await client.post(
            f"{base_url}/api/session",
            json={"api_key": api_key}
        )
        if response.status_code != 200:
            print(f"❌ Failed to create session: {response.text}")
            return
        
        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"✅ Session created: {session_id}")
        
        # Test different MCP command formats
        test_cases = [
            {
                "name": "Simple command (no env)",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": None
            },
            {
                "name": "Command with environment variable",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "your_github_token_here"}
            }
        ]
        
        for test in test_cases:
            print(f"\n2. Testing: {test['name']}")
            
            # Connect MCP
            print("   Connecting MCP server...")
            try:
                response = await client.post(
                    f"{base_url}/api/mcp/connect",
                    json={
                        "session_id": session_id,
                        "command": test["command"],
                        "args": test["args"],
                        "env": test["env"]
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    print(f"   ❌ Failed to connect: {response.text}")
                    continue
                
                result = response.json()
                if result.get("status") == "connected":
                    print("   ✅ Connected successfully!")
                    context = result.get("context", "")
                    if context:
                        print("   Available tools/resources:")
                        for line in context.split('\n')[:10]:  # Show first 10 lines
                            if line.strip():
                                print(f"     {line}")
                else:
                    print(f"   ❌ Connection failed: {result.get('error', 'Unknown error')}")
                
                # Disconnect
                print("   Disconnecting...")
                await client.post(
                    f"{base_url}/api/mcp/disconnect",
                    json={"session_id": session_id}
                )
                print("   ✅ Disconnected")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")


async def test_frontend_parsing():
    """Test the frontend command parsing logic."""
    print("\n\nTesting Frontend Command Parsing:")
    
    # Simulate frontend parsing logic
    test_commands = [
        "npx -y @modelcontextprotocol/server-github",
        "GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx npx -y @modelcontextprotocol/server-github",
        '{"command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"], "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx"}}',
        "TOKEN1=abc TOKEN2=def npx -y some-package",
    ]
    
    for command in test_commands:
        print(f"\nCommand: {command}")
        
        # This simulates the JavaScript parsing logic
        if command.startswith('{'):
            try:
                parsed = json.loads(command)
                print(f"  Type: JSON")
                print(f"  Command: {parsed.get('command')}")
                print(f"  Args: {parsed.get('args', [])}")
                print(f"  Env: {parsed.get('env', {})}")
            except:
                print("  Type: Invalid JSON")
        else:
            # Check for env vars at start
            import re
            env_pattern = r'^([A-Z_][A-Z0-9_]*=[^ ]+\s+)*'
            match = re.match(env_pattern, command)
            
            if match and match.group(0).strip():
                env_part = match.group(0).strip()
                env_vars = {}
                for pair in env_part.split():
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        env_vars[key] = value
                
                command_part = command[len(match.group(0)):].strip()
                parts = command_part.split()
                
                print(f"  Type: Command with env vars")
                print(f"  Command: {parts[0] if parts else ''}")
                print(f"  Args: {parts[1:] if len(parts) > 1 else []}")
                print(f"  Env: {env_vars}")
            else:
                parts = command.split()
                print(f"  Type: Simple command")
                print(f"  Command: {parts[0] if parts else ''}")
                print(f"  Args: {parts[1:] if len(parts) > 1 else []}")
                print(f"  Env: None")


if __name__ == "__main__":
    print("=== MCP Integration Test ===\n")
    
    # Test frontend parsing
    asyncio.run(test_frontend_parsing())
    
    # Test server integration
    print("\n\n=== Testing with Chat Server ===")
    print("Make sure the chat server is running on port 8080")
    print("Run: python chat_server.py\n")
    
    try:
        asyncio.run(test_mcp_integration())
    except httpx.ConnectError:
        print("❌ Could not connect to chat server on port 8080")
        print("   Please start the server with: python chat_server.py")