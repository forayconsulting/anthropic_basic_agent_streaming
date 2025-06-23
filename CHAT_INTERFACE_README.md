# Claude Agent Chat Interface

A lightweight web-based chat interface for testing and interacting with the Claude Agent implementation.

## Features

- 🔑 **BYOK (Bring Your Own Key)**: Enter your Anthropic API key directly in the interface
- 💬 **Real-time Streaming**: See responses as they're generated with a ChatGPT-like streaming cursor
- 🧠 **Extended Thinking Mode**: Support for Claude's thinking process with collapsible sections
- 🔧 **MCP Server Integration**: Connect to any MCP server directly from the UI
- 📝 **Conversation History**: Full multi-turn conversations with context preservation
- 💾 **Persistent Settings**: Your preferences are saved in browser local storage
- 📤 **Export Conversations**: Export your chat history as JSON

## Getting Started

### Running the Chat Interface

```bash
# Method 1: Using the launcher script (recommended)
python run_chat.py

# Method 2: Running the server directly
python chat_server.py --port 8080
```

The interface will open automatically in your default browser at `http://localhost:8080`.

### Initial Setup

1. **Enter your API Key**: Paste your Anthropic API key in the sidebar
2. **Click Connect**: This establishes a session with the server
3. **Start Chatting**: Type your message and press Enter or click Send

## Interface Overview

### Sidebar Settings

- **API Key**: Your Anthropic API key (stored locally in browser)
- **System Prompt**: Customize Claude's behavior and role
- **Thinking Budget**: Optional tokens for extended thinking (leave empty to disable)
- **Max Tokens**: Maximum response length (default: 4096)
- **Show Thinking Process**: Toggle to see Claude's thinking in collapsible sections

### MCP Server Connection

1. Enter your MCP server command (e.g., `python -m my_mcp_server`)
2. Click Connect to establish MCP connection
3. Claude will automatically have access to the MCP server's tools
4. The connection status and available context will be displayed

### Chat Features

- **Streaming Responses**: Responses appear in real-time with a blinking cursor
- **Thinking Sections**: When thinking is enabled, see Claude's reasoning process
  - Auto-collapses when the response begins
  - Click to expand/collapse at any time
  - Shows word count when complete
- **Message History**: Full conversation context is maintained
- **Clear Chat**: Start a fresh conversation
- **Export**: Download your conversation as JSON

## Technical Details

### Architecture

The chat interface consists of three main components:

1. **chat_server.py**: HTTP server that wraps the Claude Agent
   - Handles API sessions and state management
   - Provides SSE (Server-Sent Events) for streaming
   - Manages MCP connections per session

2. **chat_interface.html**: Single-file web interface
   - No external dependencies (pure HTML/CSS/JS)
   - Responsive design with collapsible sidebar
   - Real-time SSE event handling

3. **run_chat.py**: Launcher script
   - Starts the server
   - Opens the browser automatically
   - Handles graceful shutdown

### API Endpoints

- `GET /`: Serves the HTML interface
- `POST /api/session`: Create/update session with API key
- `POST /api/chat`: Stream chat responses (SSE)
- `POST /api/mcp/connect`: Connect to MCP server
- `POST /api/mcp/disconnect`: Disconnect from MCP server
- `POST /api/mcp/status`: Get MCP connection status

### Conversation History

The interface maintains full conversation history:
- Each message includes role (user/assistant) and content
- History is sent with each new message for context
- Exported conversations include all messages and settings

### Extended Thinking Mode

When thinking budget is set:
- Claude uses additional tokens for reasoning
- Thinking appears in blue collapsible sections
- Sections auto-collapse when response begins
- Useful for complex problems requiring step-by-step reasoning

## Examples

### Basic Conversation
```
You: What is the capital of France?
Claude: The capital of France is Paris.
```

### With Extended Thinking
```
You: Solve this step by step: If a train travels 120 miles in 2 hours, and then 180 miles in 3 hours, what is its average speed?
Claude: [Thinking: Let me calculate this step by step...]
The average speed is 60 miles per hour.
```

### With MCP Tools
```
MCP Command: npx -y @modelcontextprotocol/server-filesystem /Users/me/documents
You: What files are in my documents folder?
Claude: I can see the following files in your documents folder...
```

## Troubleshooting

### Connection Issues
- Ensure the server is running on the correct port
- Check that your API key is valid
- Look for error messages in the browser console

### Streaming Not Working
- Verify your browser supports Server-Sent Events
- Check for proxy or firewall interference
- Try a different browser

### MCP Connection Failed
- Ensure the MCP server command is correct
- Check that required dependencies are installed
- Look at server logs for detailed error messages

## Development

### Running Tests
```bash
# Test the chat server
pytest test_chat_server.py -v

# Test with coverage
pytest test_chat_*.py --cov=chat_server
```

### Modifying the Interface
- All UI code is in `chat_interface.html`
- Server logic is in `chat_server.py`
- No build process required - just refresh the browser

### Adding Features
The interface is designed to be minimal and extensible:
- Add new API endpoints in `chat_server.py`
- Update the UI in `chat_interface.html`
- Follow the existing patterns for consistency