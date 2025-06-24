# MCP Connection Fix Documentation

## Problem
The MCP (Model Context Protocol) connection was failing when users tried to connect to servers that require environment variables, such as the GitHub MCP server. The issue was that the frontend was naively splitting the command string on spaces, which doesn't properly handle:
- Environment variables
- Complex command arguments
- Quoted strings with spaces

## Root Cause
1. **Frontend parsing**: The `connectMCP()` function in `chat_interface.html` was using `command.split(' ')` which doesn't handle shell-style commands properly
2. **Backend limitation**: The server wasn't accepting environment variables in the API request
3. **User confusion**: No clear documentation on supported command formats

## Solution Implemented

### 1. Backend Changes (`chat_server.py`)
- Added support for `env` parameter in `handle_mcp_connect()`
- Updated `_connect_mcp()` and `_async_connect_mcp()` to pass environment variables to the agent

### 2. Frontend Changes (`chat_interface.html`)
- Implemented proper command parsing that supports three formats:
  - **Simple commands**: `npx -y @modelcontextprotocol/server-github`
  - **Commands with env vars**: `GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx npx -y @modelcontextprotocol/server-github`
  - **JSON format**: `{"command": "npx", "args": ["-y", "pkg"], "env": {"TOKEN": "value"}}`
- Added regex pattern matching to detect environment variables at the start of commands
- Updated API calls to include the `env` parameter

### 3. User Interface Improvements
- Added help text showing the three supported command formats
- Provides clear examples for each format
- Makes it easier for users to understand how to connect to MCP servers

## Usage Examples

### Example 1: GitHub MCP Server
Instead of the incorrect format:
```
npx -y @modelcontextprotocol/server-github -e GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx
```

Use one of these correct formats:

**Option A - Environment variable prefix:**
```
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx npx -y @modelcontextprotocol/server-github
```

**Option B - JSON format:**
```json
{"command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"], "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx"}}
```

### Example 2: Simple MCP Server (no env vars)
```
npx -y @modelcontextprotocol/server-filesystem
```

### Example 3: Multiple Environment Variables
```
API_KEY=abc SECRET=xyz python -m my_mcp_server --port 3000
```

## Testing
1. Run the integration test:
   ```bash
   python test_mcp_integration.py
   ```

2. Manual testing:
   - Start the chat server: `python chat_server.py`
   - Open http://localhost:8080
   - Enter your API key and connect
   - Try connecting to an MCP server using the formats above

## Benefits
1. **Flexibility**: Users can now connect to MCP servers that require environment variables
2. **Clarity**: Clear documentation and UI help text prevent confusion
3. **Compatibility**: Supports standard shell-style environment variable syntax
4. **Robustness**: JSON format provides an escape hatch for complex scenarios

## Future Improvements
1. Add a dedicated UI field for environment variables
2. Support for more complex shell features (pipes, redirects, etc.)
3. Validate MCP server commands before attempting connection
4. Show available MCP servers from a registry