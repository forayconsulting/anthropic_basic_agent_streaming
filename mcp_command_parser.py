"""MCP command parser for handling complex command strings."""

import json
import shlex
from typing import Dict, Tuple, List, Optional


def parse_mcp_command(command_string: str) -> Tuple[str, List[str], Optional[Dict[str, str]]]:
    """
    Parse MCP command string into command, args, and environment variables.
    
    Supports multiple formats:
    1. Simple: "npx -y @modelcontextprotocol/server-github"
    2. With env prefix: "GITHUB_TOKEN=abc npx -y @modelcontextprotocol/server-github"
    3. JSON format: '{"command": "npx", "args": ["-y", "pkg"], "env": {"TOKEN": "abc"}}'
    
    Returns:
        Tuple of (command, args, env_dict)
    """
    command_string = command_string.strip()
    
    # Check if it's JSON format
    if command_string.startswith('{'):
        try:
            data = json.loads(command_string)
            return (
                data.get('command', ''),
                data.get('args', []),
                data.get('env', None)
            )
        except json.JSONDecodeError:
            pass
    
    # Parse shell-style command with potential env vars
    env_vars = {}
    
    # Extract environment variables (KEY=VALUE patterns at the beginning)
    parts = shlex.split(command_string)
    command_start_idx = 0
    
    for i, part in enumerate(parts):
        if '=' in part and i == command_start_idx:
            # This looks like an env var
            key, value = part.split('=', 1)
            # Validate it's a valid env var name (alphanumeric + underscore)
            if key and key.replace('_', '').isalnum() and key[0].isalpha():
                env_vars[key] = value
                command_start_idx = i + 1
            else:
                # Not an env var, this is where the command starts
                break
        else:
            # No more env vars
            break
    
    # Get command and args
    if command_start_idx < len(parts):
        command = parts[command_start_idx]
        args = parts[command_start_idx + 1:]
    else:
        command = ''
        args = []
    
    return command, args, env_vars if env_vars else None


def format_mcp_command_help() -> str:
    """Return help text for MCP command formats."""
    return """MCP Command Formats:

1. Simple command:
   npx -y @modelcontextprotocol/server-github

2. With environment variables:
   GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx npx -y @modelcontextprotocol/server-github

3. JSON format (most flexible):
   {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"], "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx"}}

Note: Use quotes around values with spaces."""


# Test the parser
if __name__ == "__main__":
    test_cases = [
        # Simple command
        "npx -y @modelcontextprotocol/server-github",
        
        # With env var
        "GITHUB_PERSONAL_ACCESS_TOKEN=ghp_123 npx -y @modelcontextprotocol/server-github",
        
        # Multiple env vars
        "TOKEN1=abc TOKEN2=def npx -y some-package",
        
        # JSON format
        '{"command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"], "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_123"}}',
        
        # Command with quoted args
        'npx -y "some package with spaces"',
        
        # The problematic format from the user
        "npx -y @modelcontextprotocol/server-github -e GITHUB_PERSONAL_ACCESS_TOKEN=ghp_123",
    ]
    
    print("Testing MCP command parser:\n")
    for test in test_cases:
        print(f"Input: {test}")
        try:
            cmd, args, env = parse_mcp_command(test)
            print(f"  Command: {cmd}")
            print(f"  Args: {args}")
            print(f"  Env: {env}")
        except Exception as e:
            print(f"  Error: {e}")
        print()