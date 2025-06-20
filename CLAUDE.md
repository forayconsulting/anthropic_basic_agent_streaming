# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a minimal Claude-based agent implementation that provides:
- Direct integration with Claude Opus 4 API
- Support for extended thinking mode with separate thinking/response token handling
- Local MCP (Model Context Protocol) server integration
- Real-time streaming via Server-Sent Events (SSE)
- Custom UI integration capabilities

## Current Status (as of 2025-06-20)

✅ **Fully Implemented and Tested**
- SSE event parser with buffering support
- Token classifier for thinking/response distinction
- MCP client wrapper for local tool integration
- API request builder with all Claude features
- Agent orchestration layer
- 53 unit tests, all passing
- Integration tests verified with real API calls

## Architecture

The agent follows a minimal design with these core components:

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│   Custom UI     │────▶│ ClaudeAgent  │────▶│ Claude API  │
└─────────────────┘     └──────┬───────┘     └─────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │  MCP Server  │
                        └──────────────┘
```

### Component Breakdown

1. **SSE Parser** (`sse_parser.py`)
   - Handles Server-Sent Events parsing
   - Buffers incomplete events
   - Yields structured SSEEvent objects

2. **Token Classifier** (`token_classifier.py`)
   - Classifies tokens as THINKING or RESPONSE
   - Maintains state across content blocks
   - Handles thinking summaries and redacted thinking

3. **MCP Client** (`mcp_client.py`)
   - Connects to local MCP servers via stdio
   - Lists and calls tools
   - Provides context for prompts

4. **API Request Builder** (`api_request_builder.py`)
   - Builds properly formatted API requests
   - Validates parameters (thinking budget, max tokens)
   - Supports conversation history

5. **Agent Core** (`agent.py`)
   - Orchestrates all components
   - Provides simple streaming interface
   - Handles errors gracefully

## Key Implementation Details

### API Configuration
- Model: `claude-opus-4-20250514`
- API Version: `2023-06-01` (important - not 2024)
- Extended thinking: Enable with `thinking_budget` parameter
- Streaming: Always enabled for real-time responses

### MCP Integration
- Uses stdio transport for local servers
- Connection: `await agent.connect_mcp("command", ["args"])`
- Context automatically included in prompts when connected

### Token Classification
- Thinking blocks: `thinking`, `thinking_summary`, `redacted_thinking`
- Response blocks: `text`
- Classification based on `content_block` type

## Usage Examples

### Basic Usage
```python
agent = ClaudeAgent(api_key="your-key")
async for event in agent.stream_response(
    system_prompt="You are helpful",
    user_prompt="Hello"
):
    if event.type == StreamEventType.RESPONSE:
        print(event.content, end="")
```

### With Extended Thinking
```python
async for event in agent.stream_response(
    system_prompt="You are thoughtful",
    user_prompt="Complex question",
    thinking_budget=10000,
    max_tokens=20000
):
    if event.type == StreamEventType.THINKING:
        # Handle thinking differently in UI
        show_thinking(event.content)
    elif event.type == StreamEventType.RESPONSE:
        show_response(event.content)
```

### With MCP Tools
```python
await agent.connect_mcp("python", ["-m", "mcp_server"])
# Tools are now available to Claude
async for event in agent.stream_response(...):
    # Claude can use MCP tools
```

## Testing

### Unit Tests (No API Calls)
```bash
pytest -v  # 53 tests covering all components
```

### Integration Tests (Real API)
```bash
export ANTHROPIC_API_KEY='your-key'
python test_agent.py  # Comprehensive test suite
python cli.py         # Interactive testing
```

### Mock Tests
```bash
python test_mock.py  # Test without API calls
```

## Common Commands

### Development
```bash
# Install in development mode
pip install -e ".[dev]"

# Run linting
black src/ tests/
ruff src/ tests/
mypy src/

# Run specific test file
pytest tests/test_sse_parser.py -v
```

### Testing
```bash
# Quick API test
python debug_test.py

# Full test suite
python test_agent.py

# Interactive CLI
python cli.py
```

## Important Notes

1. **API Version**: Must use `2023-06-01`, not `2024-06-01`
2. **Thinking Budget**: Must be less than max_tokens
3. **Streaming**: Uses httpx with async generators
4. **MCP**: Currently supports stdio transport only
5. **Error Handling**: Errors are streamed as ERROR events

## Next Steps

The implementation is complete and tested. Ready for:
1. Integration with custom UI
2. Connection to custom MCP server
3. Production deployment

The minimal design makes it easy to extend or modify as needed.