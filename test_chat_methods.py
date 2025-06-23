#!/usr/bin/env python3
"""Unit tests for chat server methods without HTTP handler initialization."""

import unittest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import specific functions and classes we want to test
import chat_server
from claude_agent.agent import StreamEventType, StreamEvent


class TestChatServerMethods(unittest.TestCase):
    """Test chat server methods in isolation."""
    
    def setUp(self):
        """Clear sessions before each test."""
        chat_server.sessions.clear()
    
    def test_sessions_management(self):
        """Test global sessions dictionary."""
        # Test initial state
        self.assertEqual(len(chat_server.sessions), 0)
        
        # Add a session
        chat_server.sessions["test-id"] = {
            "agent": Mock(),
            "conversation_history": [],
            "system_prompt": "test",
            "thinking_budget": None,
            "max_tokens": 4096,
            "mcp_connected": False
        }
        
        self.assertEqual(len(chat_server.sessions), 1)
        self.assertIn("test-id", chat_server.sessions)
        
        # Clear sessions
        chat_server.sessions.clear()
        self.assertEqual(len(chat_server.sessions), 0)
    
    def test_sse_event_format(self):
        """Test SSE event formatting logic."""
        # Create a mock handler
        handler = MagicMock()
        handler.wfile = Mock()
        
        # Test the SSE formatting directly
        event_type = "test"
        data = "Hello World"
        expected = f'event: {event_type}\ndata: {json.dumps(data)}\n\n'
        
        # Call _send_sse_event method directly
        chat_server.ChatHandler._send_sse_event(handler, event_type, data)
        
        # Verify the write was called with correct format
        handler.wfile.write.assert_called_once_with(expected.encode('utf-8'))
        handler.wfile.flush.assert_called_once()
    
    def test_handle_session_logic(self):
        """Test session handling logic."""
        handler = MagicMock()
        handler.send_error = Mock()
        handler.send_json_response = Mock()
        
        # Test without API key
        chat_server.ChatHandler.handle_session(handler, {})
        handler.send_error.assert_called_once_with(400, "API key required")
        
        # Reset mock
        handler.send_error.reset_mock()
        
        # Test with API key
        with patch('chat_server.ClaudeAgent') as mock_agent:
            chat_server.ChatHandler.handle_session(handler, {"api_key": "test-key"})
            
            # Verify agent was created
            mock_agent.assert_called_once_with(api_key="test-key")
            
            # Verify session was created
            self.assertEqual(len(chat_server.sessions), 1)
            
            # Verify response was sent
            args = handler.send_json_response.call_args[0][0]
            self.assertIn("session_id", args)
    
    def test_handle_chat_validation(self):
        """Test chat request validation."""
        handler = MagicMock()
        handler.send_error = Mock()
        
        # Test without session_id
        chat_server.ChatHandler.handle_chat(handler, {})
        handler.send_error.assert_called_with(401, "Invalid session")
        
        # Test with invalid session_id
        handler.send_error.reset_mock()
        chat_server.ChatHandler.handle_chat(handler, {"session_id": "invalid"})
        handler.send_error.assert_called_with(401, "Invalid session")
    
    def test_handle_mcp_connect_validation(self):
        """Test MCP connect validation."""
        handler = MagicMock()
        handler.send_error = Mock()
        
        # Test without session_id
        chat_server.ChatHandler.handle_mcp_connect(handler, {})
        handler.send_error.assert_called_with(401, "Invalid session")
        
        # Test with valid session but no command
        chat_server.sessions["test-session"] = {
            "agent": Mock(),
            "mcp_connected": False
        }
        handler.send_error.reset_mock()
        chat_server.ChatHandler.handle_mcp_connect(handler, {"session_id": "test-session"})
        handler.send_error.assert_called_with(400, "Command required")
    
    def test_json_response_format(self):
        """Test JSON response formatting."""
        handler = MagicMock()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.send_cors_headers = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        
        test_data = {"key": "value", "number": 123}
        chat_server.ChatHandler.send_json_response(handler, test_data)
        
        # Verify response code
        handler.send_response.assert_called_once_with(200)
        
        # Verify headers
        handler.send_header.assert_any_call('Content-Type', 'application/json')
        
        # Verify JSON data
        written_data = handler.wfile.write.call_args[0][0]
        self.assertEqual(json.loads(written_data), test_data)
    
    def test_cors_headers(self):
        """Test CORS headers are set correctly."""
        handler = MagicMock()
        handler.send_header = Mock()
        
        chat_server.ChatHandler.send_cors_headers(handler)
        
        # Verify all CORS headers
        expected_headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
        
        for header, value in expected_headers.items():
            handler.send_header.assert_any_call(header, value)


class TestServerRouting(unittest.TestCase):
    """Test server endpoint routing logic."""
    
    def test_get_endpoint_routing(self):
        """Test GET endpoint routing logic."""
        handler = MagicMock()
        handler.path = '/'
        handler.serve_html = Mock()
        handler.send_json_response = Mock()
        handler.send_error = Mock()
        
        # Test root path
        chat_server.ChatHandler.do_GET(handler)
        handler.serve_html.assert_called_once()
        
        # Test API status
        handler.serve_html.reset_mock()
        handler.path = '/api/status'
        chat_server.ChatHandler.do_GET(handler)
        handler.send_json_response.assert_called_once_with({
            "status": "ok",
            "version": "0.1.0"
        })
        
        # Test 404
        handler.send_json_response.reset_mock()
        handler.path = '/unknown'
        chat_server.ChatHandler.do_GET(handler)
        handler.send_error.assert_called_once_with(404)
    
    def test_post_endpoint_parsing(self):
        """Test POST endpoint parsing and routing."""
        handler = MagicMock()
        handler.headers = {'Content-Length': '2'}
        handler.rfile = Mock()
        handler.rfile.read = Mock(return_value=b'{}')
        handler.send_error = Mock()
        
        # Mock handler methods
        handler.handle_session = Mock()
        handler.handle_chat = Mock()
        handler.handle_mcp_connect = Mock()
        handler.handle_mcp_disconnect = Mock()
        handler.handle_mcp_status = Mock()
        
        # Test session endpoint
        handler.path = '/api/session'
        chat_server.ChatHandler.do_POST(handler)
        handler.handle_session.assert_called_once_with({})
        
        # Test chat endpoint
        handler.path = '/api/chat'
        chat_server.ChatHandler.do_POST(handler)
        handler.handle_chat.assert_called_once_with({})
        
        # Test unknown endpoint
        handler.path = '/api/unknown'
        chat_server.ChatHandler.do_POST(handler)
        handler.send_error.assert_called_with(404)


class TestAsyncHelpers(unittest.TestCase):
    """Test async helper methods."""
    
    @patch('asyncio.new_event_loop')
    @patch('asyncio.set_event_loop')
    def test_connect_mcp_helper(self, mock_set_loop, mock_new_loop):
        """Test _connect_mcp helper method."""
        # Setup
        mock_loop = Mock()
        mock_new_loop.return_value = mock_loop
        mock_loop.run_until_complete = Mock(return_value={"status": "connected"})
        
        handler = MagicMock()
        session = {
            "agent": Mock(),
            "mcp_connected": False
        }
        
        # Run the method
        result = chat_server.ChatHandler._connect_mcp(handler, session, "test", [])
        
        # Verify
        mock_new_loop.assert_called_once()
        mock_set_loop.assert_called_once_with(mock_loop)
        mock_loop.close.assert_called_once()
        self.assertEqual(result, {"status": "connected"})


if __name__ == "__main__":
    unittest.main()