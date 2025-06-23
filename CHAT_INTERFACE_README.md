# Claude Agent Chat Interface

A lightweight web-based chat interface for testing and interacting with the Claude Agent implementation.

## Features

- **BYOK (Bring Your Own Key)**: Enter your Anthropic API key directly in the interface
- **Real-time Streaming**: See Claude's responses as they're generated
- **Extended Thinking Mode**: Toggle and configure Claude's thinking process
- **MCP Server Integration**: Connect to Model Context Protocol servers
- **Conversation History**: Full chat history with export functionality
- **Settings Persistence**: Saves your preferences in browser local storage

## Quick Start

1. **Ensure you're in the virtual environment**:
   ```bash
   source venv/bin/activate
   ```

2. **Run the chat interface**:
   ```bash
   python run_chat.py
   ```
   
   This will:
   - Start the server on http://localhost:8080
   - Automatically open your browser
   - Display the chat interface

3. **Configure and Connect**:
   - Enter your Anthropic API key
   - Click "Connect"
   - Start chatting!

## Usage

### Basic Chat
1. Enter your API key and click "Connect"
2. Type messages in the input area
3. Press Enter or click Send

### Settings
- **System Prompt**: Customize Claude's behavior
- **Thinking Budget**: Enable extended thinking (1024-128000 tokens)
- **Max Tokens**: Set response length limit
- **Show Thinking**: Toggle visibility of Claude's thinking process

### MCP Server Connection
1. Enter MCP server command (e.g., `python -m my_mcp_server`)
2. Click "Connect" in the MCP section
3. Claude can now use tools provided by the MCP server

### Additional Options
- **Clear Chat**: Remove all messages
- **Export**: Download conversation as JSON

## Command Line Options

```bash
python run_chat.py --help
```

Options:
- `--port PORT`: Run on a different port (default: 8080)
- `--no-browser`: Don't open browser automatically
- `--host HOST`: Bind to specific host (default: localhost)

## Testing

Run the test suite:
```bash
# Unit tests for server methods
python test_chat_methods.py

# Integration tests (requires httpx)
python test_chat_integration.py

# Client-side tests
open test_chat_interface.html
```

## Architecture

The chat interface consists of three main components:

1. **chat_server.py**: Minimal HTTP server that wraps the Claude Agent
2. **chat_interface.html**: Self-contained web interface with embedded CSS/JS
3. **run_chat.py**: Launcher script for easy startup

The implementation follows a minimal design philosophy:
- No external web framework (uses Python's built-in HTTP server)
- Single HTML file with embedded styles and scripts
- Direct integration with existing Claude Agent implementation

## Troubleshooting

### Server won't start
- Check if port 8080 is already in use
- Try a different port: `python run_chat.py --port 8081`

### Connection fails
- Verify your API key is correct
- Check server logs in the terminal
- Ensure you're using a valid Anthropic API key

### MCP connection issues
- Verify the MCP server command is correct
- Check that the MCP server is installed
- Look for error messages in the terminal

## Security Notes

- API keys are stored in browser local storage
- Never share or commit your API key
- The server only accepts connections from localhost by default
- For production use, implement proper authentication and HTTPS