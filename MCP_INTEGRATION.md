# MCP Integration Guide

This guide explains how to use the Claude Agent with MCP (Model Context Protocol) servers.

## Overview

The Claude Agent now supports full MCP integration, allowing Claude to use tools from your existing MCP servers (like those in Claude Desktop). This implementation includes:

- Full MCP client support with stdio transport
- Automatic tool format conversion (MCP ↔ Anthropic)
- Complete tool use cycle handling
- Streaming responses with tool execution
- Multiple tool calls in a single conversation
- Extended thinking mode with tool awareness

## Installation

Make sure you have the MCP SDK installed:

```bash
pip install mcp
```

## Basic Usage

### 1. Using the Fixed MCP Client

```python
from claude_agent.mcp_client_fixed import FixedMCPClient

client = FixedMCPClient()

# Connect to an MCP server using context manager
async with client.connect(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
) as session:
    # Tools are automatically loaded
    tools = client.tools
    print(f"Available tools: {[t.name for t in tools]}")
    
    # Get tools in Anthropic format
    anthropic_tools = client.get_anthropic_tools()
    
    # Call a tool
    result = await session.call_tool("read_file", {"path": "/tmp/example.txt"})
```

### 2. Using the Agent with Full Tool Support

```python
from claude_agent.agent_with_tools import ClaudeAgentWithTools, StreamEventType

# Create agent
agent = ClaudeAgentWithTools(api_key="your-api-key")

# Connect to MCP server
await agent.connect_mcp(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
)

# Stream response with automatic tool handling
async for event in agent.stream_response_with_tools(
    system_prompt="You are a helpful assistant with filesystem access.",
    user_prompt="What files are in the /tmp directory and what do they contain?"
):
    if event.type == StreamEventType.RESPONSE:
        print(event.content, end="", flush=True)
    elif event.type == StreamEventType.TOOL_USE:
        print(f"\n[Tool: {event.content}]")
    elif event.type == StreamEventType.TOOL_RESULT:
        print(f"\n[Result: {event.metadata}]")

# Disconnect when done
await agent.disconnect_mcp()
```

### 3. Using the Connection Manager

```python
from claude_agent.mcp_client_fixed import MCPConnectionManager

# For persistent connections across multiple requests
manager = MCPConnectionManager()

# Connect once
await manager.connect(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-youtube-transcript"]
)

# Use multiple times
tools = manager.get_anthropic_tools()
result = await manager.call_tool("get_transcript", {"url": "https://youtube.com/..."})

# Disconnect when done
await manager.disconnect()
```

## Working with Claude Desktop MCP Servers

If you have Claude Desktop installed, you can use your existing MCP servers:

```python
import json
from pathlib import Path

# Load Claude Desktop config
config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
with open(config_path) as f:
    config = json.load(f)

# Connect to a configured server
server_config = config['mcpServers']['filesystem']
await agent.connect_mcp(
    command=server_config['command'],
    args=server_config['args'],
    env=server_config.get('env', {})
)
```

## Available MCP Servers

Common MCP servers you can use:

1. **Filesystem Server**
   ```bash
   npx -y @modelcontextprotocol/server-filesystem /path/to/directory
   ```

2. **GitHub Server**
   ```bash
   npx -y @modelcontextprotocol/server-github
   # Requires GITHUB_PERSONAL_ACCESS_TOKEN env var
   ```

3. **SQLite Server**
   ```bash
   mcp-server-sqlite --db-path /path/to/database.db
   ```

## Extended Thinking with MCP

The agent supports extended thinking mode with MCP context:

```python
thinking_tokens = []
response_tokens = []

async for event in agent.stream_response(
    system_prompt="You are a helpful assistant with MCP tools.",
    user_prompt="Analyze the project structure and suggest improvements.",
    thinking_budget=10000,  # Allow up to 10k thinking tokens
    include_mcp_context=True
):
    if event.type == StreamEventType.THINKING:
        thinking_tokens.append(event.content)
    elif event.type == StreamEventType.RESPONSE:
        response_tokens.append(event.content)
        print(event.content, end="", flush=True)

print(f"\nThinking used {len(thinking_tokens)} tokens")
```

## Error Handling

Always handle connection errors and disconnection:

```python
try:
    await agent.connect_mcp(command="mcp-server", args=["--config", "config.json"])
    
    # Use the agent...
    
except Exception as e:
    print(f"MCP Error: {e}")
    
finally:
    await agent.disconnect_mcp()
```

## Testing MCP Integration

Use the provided test scripts to verify your MCP setup:

1. **Basic connection test**: `python test_mcp_basic.py`
2. **Local servers test**: `python test_local_mcp_servers.py`
3. **Simple integration test**: `python test_mcp_simple.py`
4. **Full demo**: `python example_mcp_usage.py`

## Important Notes

1. **Node.js Requirement**: Most MCP servers are Node.js packages and require Node.js/npm to be installed.

2. **Stdio Transport**: This implementation uses stdio transport, which spawns the MCP server as a subprocess.

3. **Security**: Be careful with environment variables containing API keys or secrets. The test scripts mask sensitive data.

4. **Async Context**: All MCP operations are asynchronous and should be used with `async/await`.

5. **Connection Lifecycle**: Always disconnect from MCP servers when done to clean up resources.

## Troubleshooting

### Server Won't Connect
- Ensure the MCP server command is installed and accessible
- Check that Node.js and npm are installed for npx-based servers
- Verify environment variables are set correctly

### Tools Not Available
- Some servers take time to initialize
- Check server logs for errors
- Ensure the server has the necessary permissions

### Timeouts
- MCP servers may take time to start, especially on first run
- Increase timeout values if needed
- Check system resources

## Next Steps

1. Install MCP servers relevant to your use case
2. Configure environment variables as needed
3. Test the integration with your MCP servers
4. Build applications that leverage Claude + MCP capabilities

For more information about MCP, visit the [MCP documentation](https://modelcontextprotocol.io/docs).