#!/usr/bin/env python3
"""Tests for the chat server."""

import unittest
import json
import threading
import time
import httpx
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from http.server import HTTPServer

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chat_server import ChatHandler, run_server, sessions
from claude_agent.agent import StreamEventType, StreamEvent


class TestChatServer(unittest.TestCase):
    """Test cases for chat server."""
    
    @classmethod
    def setUpClass(cls):
        """Start the test server."""
        cls.server_thread = threading.Thread(
            target=run_server,
            args=(8081,),
            daemon=True
        )
        cls.server_thread.start()
        time.sleep(1)  # Give server time to start
        cls.base_url = "http://localhost:8081"
    
    def setUp(self):
        """Clear sessions before each test."""
        sessions.clear()
    
    def test_server_status(self):
        """Test that server is running and responds to status endpoint."""
        with httpx.Client() as client:
            response = client.get(f"{self.base_url}/api/status")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["version"], "0.1.0")
    
    def test_cors_headers(self):
        """Test that CORS headers are properly set."""
        with httpx.Client() as client:
            response = client.options(f"{self.base_url}/api/status")
            self.assertEqual(response.status_code, 200)
            self.assertIn("access-control-allow-origin", response.headers)
            self.assertEqual(response.headers["access-control-allow-origin"], "*")
    
    def test_create_session_without_api_key(self):
        """Test session creation fails without API key."""
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/api/session",
                json={}
            )
            self.assertEqual(response.status_code, 400)
    
    def test_create_session_with_api_key(self):
        """Test session creation with API key."""
        with patch('chat_server.ClaudeAgent') as mock_agent:
            with httpx.Client() as client:
                response = client.post(
                    f"{self.base_url}/api/session",
                    json={"api_key": "test-key"}
                )
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIn("session_id", data)
                self.assertTrue(len(data["session_id"]) > 0)
                
                # Verify agent was created
                mock_agent.assert_called_once_with(api_key="test-key")
    
    def test_chat_without_session(self):
        """Test chat fails without valid session."""
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/api/chat",
                json={"message": "Hello"}
            )
            self.assertEqual(response.status_code, 401)
    
    def test_chat_streaming(self):
        """Test chat streaming with mock agent."""
        # First create a session
        with patch('chat_server.ClaudeAgent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent
            
            with httpx.Client() as client:
                # Create session
                session_response = client.post(
                    f"{self.base_url}/api/session",
                    json={"api_key": "test-key"}
                )
                session_id = session_response.json()["session_id"]
                
                # Mock streaming response
                async def mock_stream():
                    yield StreamEvent(StreamEventType.THINKING, "Thinking...", {})
                    yield StreamEvent(StreamEventType.RESPONSE, "Hello!", {})
                
                mock_agent.stream_response = AsyncMock(return_value=mock_stream())
                
                # Test chat - this would need a proper SSE client to test streaming
                # For now, just verify the endpoint accepts the request
                with client.stream("POST",
                    f"{self.base_url}/api/chat",
                    json={
                        "session_id": session_id,
                        "message": "Hello"
                    }
                ) as response:
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.headers["content-type"], "text/event-stream")
    
    def test_mcp_connect_without_session(self):
        """Test MCP connect fails without session."""
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/api/mcp/connect",
                json={"command": "test"}
            )
            self.assertEqual(response.status_code, 401)
    
    def test_mcp_connect_without_command(self):
        """Test MCP connect fails without command."""
        # Create session first
        with patch('chat_server.ClaudeAgent'):
            with httpx.Client() as client:
                session_response = client.post(
                    f"{self.base_url}/api/session",
                    json={"api_key": "test-key"}
                )
                session_id = session_response.json()["session_id"]
                
                response = client.post(
                    f"{self.base_url}/api/mcp/connect",
                    json={"session_id": session_id}
                )
                self.assertEqual(response.status_code, 400)
    
    def test_mcp_status(self):
        """Test MCP status endpoint."""
        # Create session
        with patch('chat_server.ClaudeAgent'):
            with httpx.Client() as client:
                session_response = client.post(
                    f"{self.base_url}/api/session",
                    json={"api_key": "test-key"}
                )
                session_id = session_response.json()["session_id"]
                
                # Check status
                response = client.post(
                    f"{self.base_url}/api/mcp/status",
                    json={"session_id": session_id}
                )
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertFalse(data["connected"])
                self.assertEqual(data["status"], "disconnected")
    
    def test_404_for_unknown_endpoints(self):
        """Test 404 response for unknown endpoints."""
        with httpx.Client() as client:
            response = client.get(f"{self.base_url}/api/unknown")
            self.assertEqual(response.status_code, 404)
            
            response = client.post(f"{self.base_url}/api/unknown", json={})
            self.assertEqual(response.status_code, 404)


class TestChatHandlerUnit(unittest.TestCase):
    """Unit tests for ChatHandler methods."""
    
    def test_send_sse_event(self):
        """Test SSE event formatting."""
        handler = ChatHandler(Mock(), ('127.0.0.1', 12345), Mock())
        handler.wfile = Mock()
        
        handler._send_sse_event("test", "Hello")
        
        expected = 'event: test\ndata: "Hello"\n\n'
        handler.wfile.write.assert_called_once_with(expected.encode('utf-8'))
        handler.wfile.flush.assert_called_once()
    
    def test_session_management(self):
        """Test session creation and storage."""
        handler = ChatHandler(Mock(), ('127.0.0.1', 12345), Mock())
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        
        with patch('chat_server.ClaudeAgent') as mock_agent:
            # Create session
            handler.handle_session({"api_key": "test-key"})
            
            # Verify session was created
            self.assertEqual(len(sessions), 1)
            session_id = list(sessions.keys())[0]
            session = sessions[session_id]
            
            self.assertEqual(session['system_prompt'], 'You are a helpful assistant.')
            self.assertEqual(session['max_tokens'], 4096)
            self.assertIsNone(session['thinking_budget'])
            self.assertFalse(session['mcp_connected'])
            self.assertEqual(len(session['conversation_history']), 0)


if __name__ == "__main__":
    unittest.main()