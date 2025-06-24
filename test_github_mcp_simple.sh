#!/bin/bash
# Simple test of GitHub MCP server

echo "Testing GitHub MCP server directly..."
echo "=================================="

TOKEN="your_github_token_here"

echo -e "\n1. Testing if npx can find the package:"
npx -y @modelcontextprotocol/server-github --help 2>&1 | head -20

echo -e "\n2. Testing with environment variable:"
GITHUB_PERSONAL_ACCESS_TOKEN="$TOKEN" npx -y @modelcontextprotocol/server-github --version 2>&1

echo -e "\n3. Checking what the server outputs on startup:"
echo '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"capabilities":{}}}' | \
  GITHUB_PERSONAL_ACCESS_TOKEN="$TOKEN" npx -y @modelcontextprotocol/server-github 2>&1 | head -50

echo -e "\nDone."