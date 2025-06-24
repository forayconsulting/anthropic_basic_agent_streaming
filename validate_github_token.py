#!/usr/bin/env python3
"""Validate GitHub personal access token."""

import httpx
import asyncio
import sys


async def validate_github_token(token: str):
    """Check if a GitHub token is valid by making an API request."""
    
    print(f"Validating GitHub token: {token[:10]}...{token[-4:]}")
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Test the token by getting user info
            response = await client.get(
                "https://api.github.com/user",
                headers=headers
            )
            
            if response.status_code == 200:
                user_data = response.json()
                print(f"✅ Token is valid!")
                print(f"   User: {user_data.get('login', 'Unknown')}")
                print(f"   Name: {user_data.get('name', 'Unknown')}")
                print(f"   Created: {user_data.get('created_at', 'Unknown')}")
                
                # Check token permissions
                scopes = response.headers.get("X-OAuth-Scopes", "").split(", ")
                if scopes and scopes[0]:
                    print(f"   Scopes: {', '.join(scopes)}")
                else:
                    print("   Scopes: No specific scopes (fine-grained token or full access)")
                
                return True
                
            elif response.status_code == 401:
                print("❌ Token is invalid or expired")
                print(f"   Response: {response.text}")
                return False
                
            else:
                print(f"❌ Unexpected response: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error validating token: {e}")
            return False


async def main():
    # The token from the screenshot
    token = "your_github_token_here"
    
    print("GitHub Token Validation")
    print("=" * 50)
    
    is_valid = await validate_github_token(token)
    
    if not is_valid:
        print("\nThe token appears to be invalid. This explains why no tools are available.")
        print("You need a valid GitHub Personal Access Token to use the GitHub MCP server.")
        print("\nTo create a new token:")
        print("1. Go to https://github.com/settings/tokens")
        print("2. Click 'Generate new token (classic)'")
        print("3. Give it a name and select the scopes you need")
        print("4. Copy the token and use it in the MCP connection")


if __name__ == "__main__":
    asyncio.run(main())