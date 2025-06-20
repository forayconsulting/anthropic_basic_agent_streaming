# Claude Agent

A minimal Python implementation of a Claude-based agent with MCP (Model Context Protocol) support and extended thinking capabilities.

## Features

- 🚀 **Streaming Responses**: Real-time token streaming via Server-Sent Events (SSE)
- 🧠 **Extended Thinking**: Support for Claude's extended thinking mode with separate thinking/response token classification
- 🔧 **MCP Integration**: Connect to local MCP servers via stdio transport
- 💬 **Conversation History**: Maintain context across multiple interactions
- 🎯 **Type-Safe**: Full type hints throughout the codebase
- ✅ **Test-Driven**: Comprehensive test coverage using TDD methodology

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd claude_agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

## Quick Start

```python
import asyncio
from claude_agent.agent import ClaudeAgent, StreamEventType

async def main():
    # Initialize agent
    agent = ClaudeAgent(api_key="your-api-key")
    
    # Stream a response
    async for event in agent.stream_response(
        system_prompt="You are a helpful assistant.",
        user_prompt="Hello, how are you?"
    ):
        if event.type == StreamEventType.RESPONSE:
            print(event.content, end="", flush=True)

asyncio.run(main())
```

## Extended Thinking Mode

Enable Claude's extended thinking for complex reasoning tasks:

```python
async for event in agent.stream_response(
    system_prompt="You are a math tutor.",
    user_prompt="Solve this complex problem...",
    thinking_budget=10000,  # Tokens for thinking
    max_tokens=20000       # Total max tokens
):
    if event.type == StreamEventType.THINKING:
        print(f"[Thinking] {event.content}")
    elif event.type == StreamEventType.RESPONSE:
        print(event.content, end="")
```

## MCP Integration

Connect to local MCP servers for tool access:

```python
# Connect to MCP server
await agent.connect_mcp("python", ["-m", "my_mcp_server"])

# Use tools in conversation
async for event in agent.stream_response(
    system_prompt="You are an assistant with tool access.",
    user_prompt="Search for information about Python."
):
    print(event.content, end="")

# Disconnect when done
await agent.disconnect_mcp()
```

## Architecture

The agent follows a modular design with clear separation of concerns:

- **SSE Parser**: Handles Server-Sent Events parsing with buffering support
- **Token Classifier**: Classifies tokens as thinking or response based on content blocks
- **MCP Client**: Manages connections to Model Context Protocol servers
- **API Request Builder**: Constructs properly formatted API requests
- **Agent Core**: Orchestrates all components for seamless streaming

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=claude_agent

# Run specific test file
pytest tests/test_sse_parser.py -v
```

## Development

This project follows Test-Driven Development (TDD) principles. When adding new features:

1. Write tests first
2. Run tests to see them fail
3. Implement the feature
4. Run tests to see them pass
5. Refactor if needed

## Requirements

- Python 3.9+
- httpx for async HTTP requests
- mcp for Model Context Protocol support
- pytest for testing

## License

MIT License - See LICENSE file for details