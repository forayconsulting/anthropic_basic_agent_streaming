#!/usr/bin/env python3
"""Simple tests for the chat server using only standard library."""

import unittest
import json
import threading
import time
import urllib.request
import urllib.error
from unittest.mock import Mock, patch, AsyncMock
import asyncio

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chat_server import ChatHandler, sessions, run_server
from claude_agent.agent import StreamEventType, StreamEvent


class TestChatServerSimple(unittest.TestCase):
    """Simple test cases for chat server using urllib."""
    
    def setUp(self):
        """Clear sessions before each test."""
        sessions.clear()
    
    def test_server_can_start(self):
        """Test that server can be imported and handler created."""
        # Just test that we can create a handler
        handler = ChatHandler(Mock(), ('127.0.0.1', 12345), Mock())
        self.assertIsNotNone(handler)
    
    def test_session_creation_logic(self):
        """Test session creation logic directly."""
        handler = ChatHandler(Mock(), ('127.0.0.1', 12345), Mock())
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        handler.send_cors_headers = Mock()
        
        # Test without API key
        handler.send_error = Mock()
        handler.handle_session({})
        handler.send_error.assert_called_once_with(400, "API key required")
        
        # Test with API key
        with patch('chat_server.ClaudeAgent') as mock_agent:
            handler.handle_session({"api_key": "test-key"})
            mock_agent.assert_called_once_with(api_key="test-key")
            self.assertEqual(len(sessions), 1)
    
    def test_cors_headers_method(self):
        """Test CORS headers are set correctly."""
        handler = ChatHandler(Mock(), ('127.0.0.1', 12345), Mock())
        handler.send_header = Mock()
        
        handler.send_cors_headers()
        
        # Check all CORS headers were sent
        calls = handler.send_header.call_args_list
        headers_sent = {call[0][0]: call[0][1] for call in calls}
        
        self.assertEqual(headers_sent['Access-Control-Allow-Origin'], '*')
        self.assertEqual(headers_sent['Access-Control-Allow-Methods'], 'GET, POST, OPTIONS')
        self.assertEqual(headers_sent['Access-Control-Allow-Headers'], 'Content-Type')
    
    def test_sse_event_formatting(self):
        """Test SSE event formatting."""
        handler = ChatHandler(Mock(), ('127.0.0.1', 12345), Mock())
        handler.wfile = Mock()
        
        handler._send_sse_event("test", "Hello World")
        
        expected = 'event: test\ndata: "Hello World"\n\n'
        handler.wfile.write.assert_called_once_with(expected.encode('utf-8'))
    
    def test_json_response(self):
        """Test JSON response method."""
        handler = ChatHandler(Mock(), ('127.0.0.1', 12345), Mock())
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.send_cors_headers = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        
        test_data = {"key": "value", "number": 123}
        handler.send_json_response(test_data)
        
        # Check response was sent correctly
        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_any_call('Content-Type', 'application/json')
        
        # Check JSON was written
        written_data = handler.wfile.write.call_args[0][0]
        self.assertEqual(json.loads(written_data.decode('utf-8')), test_data)
    
    def test_chat_validation(self):
        """Test chat endpoint validation."""
        handler = ChatHandler(Mock(), ('127.0.0.1', 12345), Mock())
        handler.send_error = Mock()
        
        # Test without session
        handler.handle_chat({})
        handler.send_error.assert_called_with(401, "Invalid session")
        
        # Test with invalid session
        handler.send_error.reset_mock()
        handler.handle_chat({"session_id": "invalid"})
        handler.send_error.assert_called_with(401, "Invalid session")
    
    def test_mcp_validation(self):
        """Test MCP endpoint validation."""
        handler = ChatHandler(Mock(), ('127.0.0.1', 12345), Mock())
        handler.send_error = Mock()
        
        # Test connect without session
        handler.handle_mcp_connect({})
        handler.send_error.assert_called_with(401, "Invalid session")
        
        # Test with session but no command
        sessions["test-session"] = {
            'agent': Mock(),
            'mcp_connected': False
        }
        handler.send_error.reset_mock()
        handler.handle_mcp_connect({"session_id": "test-session"})
        handler.send_error.assert_called_with(400, "Command required")


class TestHTTPMethodRouting(unittest.TestCase):
    """Test HTTP method routing."""
    
    def test_get_routing(self):
        """Test GET request routing."""
        handler = ChatHandler(Mock(), ('127.0.0.1', 12345), Mock())
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        handler.send_error = Mock()
        handler.send_json_response = Mock()
        handler.serve_html = Mock()
        
        # Test root path
        handler.path = '/'
        handler.do_GET()
        handler.serve_html.assert_called_once()
        
        # Test status endpoint
        handler.serve_html.reset_mock()
        handler.path = '/api/status'
        handler.do_GET()
        handler.send_json_response.assert_called_once_with({"status": "ok", "version": "0.1.0"})
        
        # Test unknown path
        handler.send_json_response.reset_mock()
        handler.path = '/unknown'
        handler.do_GET()
        handler.send_error.assert_called_once_with(404)
    
    def test_post_routing(self):
        """Test POST request routing."""
        handler = ChatHandler(Mock(), ('127.0.0.1', 12345), Mock())
        handler.rfile = Mock()
        handler.rfile.read = Mock(return_value=b'{}')
        handler.headers = {'Content-Length': '2'}
        handler.send_error = Mock()
        
        # Mock handler methods
        handler.handle_session = Mock()
        handler.handle_chat = Mock()
        handler.handle_mcp_connect = Mock()
        handler.handle_mcp_disconnect = Mock()
        handler.handle_mcp_status = Mock()
        
        # Test session endpoint
        handler.path = '/api/session'
        handler.do_POST()
        handler.handle_session.assert_called_once_with({})
        
        # Test chat endpoint
        handler.handle_session.reset_mock()
        handler.path = '/api/chat'
        handler.do_POST()
        handler.handle_chat.assert_called_once_with({})
        
        # Test MCP endpoints
        handler.path = '/api/mcp/connect'
        handler.do_POST()
        handler.handle_mcp_connect.assert_called_once()
        
        handler.path = '/api/mcp/disconnect'
        handler.do_POST()
        handler.handle_mcp_disconnect.assert_called_once()
        
        handler.path = '/api/mcp/status'
        handler.do_POST()
        handler.handle_mcp_status.assert_called_once()
        
        # Test unknown endpoint
        handler.path = '/api/unknown'
        handler.do_POST()
        handler.send_error.assert_called_with(404)


if __name__ == "__main__":
    unittest.main()