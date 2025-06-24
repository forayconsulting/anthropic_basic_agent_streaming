#!/usr/bin/env python3
"""Minimal HTTP server for Claude Agent chat interface."""

import asyncio
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import sys
import os
from typing import Optional, Dict, Any, List
import uuid
from concurrent.futures import ThreadPoolExecutor
import threading

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from claude_agent.agent import ClaudeAgent, StreamEventType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state (minimal approach for testing)
sessions: Dict[str, Dict[str, Any]] = {}
executor = ThreadPoolExecutor(max_workers=10)

class ChatHandler(BaseHTTPRequestHandler):
    """HTTP request handler for chat interface."""
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            # Serve the HTML interface
            self.serve_html()
        elif parsed_path.path == '/api/status':
            # Server status endpoint
            self.send_json_response({"status": "ok", "version": "0.1.0"})
        else:
            self.send_error(404)
    
    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return
        
        # Route to appropriate handler
        if parsed_path.path == '/api/session':
            self.handle_session(data)
        elif parsed_path.path == '/api/chat':
            self.handle_chat(data)
        elif parsed_path.path == '/api/mcp/connect':
            self.handle_mcp_connect(data)
        elif parsed_path.path == '/api/mcp/disconnect':
            self.handle_mcp_disconnect(data)
        elif parsed_path.path == '/api/mcp/status':
            self.handle_mcp_status(data)
        else:
            self.send_error(404)
    
    def serve_html(self):
        """Serve the HTML interface."""
        html_path = os.path.join(os.path.dirname(__file__), 'chat_interface.html')
        if os.path.exists(html_path):
            with open(html_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404, "chat_interface.html not found")
    
    def handle_session(self, data: Dict[str, Any]):
        """Create or update a session."""
        session_id = data.get('session_id') or str(uuid.uuid4())
        api_key = data.get('api_key', '')
        
        if not api_key:
            self.send_error(400, "API key required")
            return
        
        # Create or update session
        if session_id not in sessions:
            sessions[session_id] = {
                'agent': ClaudeAgent(api_key=api_key),
                'conversation_history': [],
                'system_prompt': 'You are a helpful assistant.',
                'thinking_budget': None,
                'max_tokens': 4096,
                'mcp_connected': False
            }
        else:
            # Update API key if provided
            sessions[session_id]['agent'] = ClaudeAgent(api_key=api_key)
        
        self.send_json_response({'session_id': session_id})
    
    def handle_chat(self, data: Dict[str, Any]):
        """Handle chat messages with streaming."""
        session_id = data.get('session_id')
        if not session_id or session_id not in sessions:
            self.send_error(401, "Invalid session")
            return
        
        session = sessions[session_id]
        message = data.get('message', '')
        
        # Update session settings if provided
        if 'system_prompt' in data:
            session['system_prompt'] = data['system_prompt']
        if 'thinking_budget' in data:
            session['thinking_budget'] = data['thinking_budget']
        if 'max_tokens' in data:
            session['max_tokens'] = data['max_tokens']
        if 'conversation_history' in data:
            session['conversation_history'] = data['conversation_history']
        
        # Debug log
        logger.info(f"Chat request - thinking_budget: {session['thinking_budget']}, max_tokens: {session['max_tokens']}, history_length: {len(session['conversation_history'])}")
        
        # Set up SSE response
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'close')  # Close connection after streaming
        self.send_cors_headers()
        self.end_headers()
        
        # Stream response in a separate thread
        future = executor.submit(self._stream_response, session, message)
        
        try:
            future.result(timeout=300)  # 5 minute timeout
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            self._send_sse_event("error", str(e))
    
    def _stream_response(self, session: Dict[str, Any], message: str):
        """Stream response from agent (runs in thread pool)."""
        # Use asyncio.run if available (Python 3.7+)
        if sys.version_info >= (3, 7):
            asyncio.run(self._async_stream_response(session, message))
        else:
            # Fallback for older Python versions
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(self._async_stream_response(session, message))
            finally:
                # Shutdown async generators
                try:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except:
                    pass
                
                # Cancel remaining tasks
                try:
                    pending = asyncio.all_tasks(loop)
                except AttributeError:
                    # Python 3.6 compatibility
                    pending = asyncio.Task.all_tasks(loop)
                
                for task in pending:
                    task.cancel()
                
                # Give tasks a chance to finish
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                
                # Close the loop
                loop.close()
    
    async def _async_stream_response(self, session: Dict[str, Any], message: str):
        """Async streaming implementation."""
        agent = session['agent']
        response_parts = []
        
        try:
            logger.info("Starting stream_response")
            async for event in agent.stream_response(
                system_prompt=session['system_prompt'],
                user_prompt=message,
                thinking_budget=session['thinking_budget'],
                max_tokens=session['max_tokens'],
                conversation_history=session['conversation_history']
            ):
                if event.type == StreamEventType.THINKING:
                    logger.debug(f"Streaming thinking token: {repr(event.content[:20])}")
                    self._send_sse_event("thinking", event.content)
                elif event.type == StreamEventType.RESPONSE:
                    response_parts.append(event.content)
                    self._send_sse_event("response", event.content)
                elif event.type == StreamEventType.ERROR:
                    self._send_sse_event("error", event.content)
            
            logger.info("Stream loop completed - updating conversation history")
            
            # Update conversation history
            session['conversation_history'].append({"role": "user", "content": message})
            if response_parts:
                session['conversation_history'].append({
                    "role": "assistant",
                    "content": "".join(response_parts)
                })
            
            # Send done event
            logger.info("Sending done event")
            self._send_sse_event("done", "")
            logger.info("Stream completed successfully")
            
        except (BrokenPipeError, ConnectionResetError) as e:
            logger.warning(f"Client disconnected during streaming: {e}")
            # Don't try to send error event if client is gone
        except Exception as e:
            logger.error(f"Error in streaming: {e}", exc_info=True)
            try:
                self._send_sse_event("error", str(e))
            except:
                pass  # Client might be disconnected
    
    def handle_mcp_connect(self, data: Dict[str, Any]):
        """Handle MCP connection."""
        session_id = data.get('session_id')
        if not session_id or session_id not in sessions:
            self.send_error(401, "Invalid session")
            return
        
        session = sessions[session_id]
        command = data.get('command', '')
        args = data.get('args', [])
        
        if not command:
            self.send_error(400, "Command required")
            return
        
        # Connect in a separate thread
        future = executor.submit(self._connect_mcp, session, command, args)
        
        try:
            result = future.result(timeout=10)
            self.send_json_response(result)
        except Exception as e:
            self.send_error(500, str(e))
    
    def _connect_mcp(self, session: Dict[str, Any], command: str, args: List[str]):
        """Connect to MCP server (runs in thread pool)."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(self._async_connect_mcp(session, command, args))
            return result
        finally:
            loop.close()
    
    async def _async_connect_mcp(self, session: Dict[str, Any], command: str, args: List[str]):
        """Async MCP connection."""
        try:
            agent = session['agent']
            await agent.connect_mcp(command, args)
            session['mcp_connected'] = True
            
            # Get context
            context = await agent._mcp_client.get_context()
            return {"status": "connected", "context": context}
        except Exception as e:
            logger.error(f"MCP connection error: {e}")
            return {"status": "error", "error": str(e)}
    
    def handle_mcp_disconnect(self, data: Dict[str, Any]):
        """Handle MCP disconnection."""
        session_id = data.get('session_id')
        if not session_id or session_id not in sessions:
            self.send_error(401, "Invalid session")
            return
        
        session = sessions[session_id]
        
        # Disconnect in a separate thread
        future = executor.submit(self._disconnect_mcp, session)
        
        try:
            future.result(timeout=5)
            session['mcp_connected'] = False
            self.send_json_response({"status": "disconnected"})
        except Exception as e:
            self.send_error(500, str(e))
    
    def _disconnect_mcp(self, session: Dict[str, Any]):
        """Disconnect from MCP server (runs in thread pool)."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(session['agent'].disconnect_mcp())
        finally:
            loop.close()
    
    def handle_mcp_status(self, data: Dict[str, Any]):
        """Get MCP status."""
        session_id = data.get('session_id')
        if not session_id or session_id not in sessions:
            self.send_error(401, "Invalid session")
            return
        
        session = sessions[session_id]
        self.send_json_response({
            "connected": session['mcp_connected'],
            "status": "connected" if session['mcp_connected'] else "disconnected"
        })
    
    def send_json_response(self, data: Dict[str, Any]):
        """Send JSON response."""
        content = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(content)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(content)
    
    def send_cors_headers(self):
        """Send CORS headers."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def _send_sse_event(self, event_type: str, data: str):
        """Send Server-Sent Event."""
        try:
            event = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
            self.wfile.write(event.encode('utf-8'))
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError) as e:
            logger.warning(f"Client disconnected: {e}")
            raise  # Re-raise to stop the stream
        except Exception as e:
            logger.error(f"Error sending SSE event: {e}")
            raise  # Re-raise to stop the stream
    
    def log_message(self, format, *args):
        """Override to reduce logging noise."""
        # Only log API requests, not all static file requests
        if args and len(args) > 0 and isinstance(args[0], str) and '/api/' in args[0]:
            logger.info(f"{self.address_string()} - {args[0]}")


def run_server(port: int = 8080):
    """Run the HTTP server."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, ChatHandler)
    
    logger.info(f"Chat server running on http://localhost:{port}")
    logger.info("Press Ctrl+C to stop")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nShutting down server...")
        httpd.shutdown()
        executor.shutdown(wait=True)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Claude Agent Chat Server")
    parser.add_argument('--port', type=int, default=8080, help='Port to run on')
    args = parser.parse_args()
    
    run_server(args.port)