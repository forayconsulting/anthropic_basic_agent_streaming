#!/usr/bin/env python3
"""Validate GitHub token using urllib."""

import urllib.request
import urllib.error
import json


def validate_github_token(token):
    """Check if a GitHub token is valid."""
    
    print(f"Validating GitHub token: {token[:10]}...{token[-4:]}")
    
    # Create request with auth header
    req = urllib.request.Request("https://api.github.com/user")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            print(f"✅ Token is valid!")
            print(f"   User: {data.get('login', 'Unknown')}")
            print(f"   Name: {data.get('name', 'Unknown')}")
            
            # Check scopes from headers
            scopes = response.headers.get("X-OAuth-Scopes", "")
            if scopes:
                print(f"   Scopes: {scopes}")
            
            return True
            
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("❌ Token is invalid or expired")
        else:
            print(f"❌ HTTP Error {e.code}: {e.reason}")
        
        # Try to read error message
        try:
            error_data = json.loads(e.read().decode())
            print(f"   Message: {error_data.get('message', 'Unknown error')}")
        except:
            pass
            
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    # The token from the screenshot
    token = "your_github_token_here"
    
    print("GitHub Token Validation")
    print("=" * 50)
    
    is_valid = validate_github_token(token)
    
    if not is_valid:
        print("\nThe token appears to be invalid. This explains why no tools are available.")
        print("The GitHub MCP server likely starts but provides no tools with an invalid token.")
        print("\nTo fix this:")
        print("1. Get a valid GitHub Personal Access Token from https://github.com/settings/tokens")
        print("2. Use the correct format in the MCP command field:")
        print("   GITHUB_PERSONAL_ACCESS_TOKEN=your_valid_token npx -y @modelcontextprotocol/server-github")
        print("   OR")
        print('   {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"], "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "your_valid_token"}}')