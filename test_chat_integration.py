#!/usr/bin/env python3
"""Integration tests for the chat interface."""

import unittest
import subprocess
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Only import httpx if available, otherwise skip integration tests
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


class TestChatIntegration(unittest.TestCase):
    """Integration tests that require the server to be running."""
    
    @classmethod
    def setUpClass(cls):
        """Start the test server."""
        if not HTTPX_AVAILABLE:
            return
            
        cls.server_process = subprocess.Popen(
            [sys.executable, 'chat_server.py', '--port', '8082'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(2)  # Give server time to start
        cls.base_url = "http://localhost:8082"
    
    @classmethod
    def tearDownClass(cls):
        """Stop the test server."""
        if not HTTPX_AVAILABLE:
            return
            
        if hasattr(cls, 'server_process'):
            cls.server_process.terminate()
            cls.server_process.wait(timeout=5)
    
    @unittest.skipIf(not HTTPX_AVAILABLE, "httpx not available")
    def test_server_responds(self):
        """Test that server is running and responds."""
        with httpx.Client() as client:
            response = client.get(f"{self.base_url}/api/status")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "ok")
    
    @unittest.skipIf(not HTTPX_AVAILABLE, "httpx not available")
    def test_html_interface_served(self):
        """Test that HTML interface is served."""
        with httpx.Client() as client:
            response = client.get(self.base_url)
            self.assertEqual(response.status_code, 200)
            self.assertIn('text/html', response.headers.get('content-type', ''))
            self.assertIn('Claude Agent Chat Interface', response.text)
    
    @unittest.skipIf(not HTTPX_AVAILABLE, "httpx not available")
    def test_session_lifecycle(self):
        """Test creating a session and using it."""
        with httpx.Client() as client:
            # Create session should fail without API key
            response = client.post(
                f"{self.base_url}/api/session",
                json={}
            )
            self.assertEqual(response.status_code, 400)
            
            # Create session with mock API key
            response = client.post(
                f"{self.base_url}/api/session",
                json={"api_key": "test-key-123"}
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("session_id", data)
            session_id = data["session_id"]
            
            # Use session for MCP status
            response = client.post(
                f"{self.base_url}/api/mcp/status",
                json={"session_id": session_id}
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertFalse(data["connected"])


class TestChatFiles(unittest.TestCase):
    """Test that all required files exist."""
    
    def test_files_exist(self):
        """Test that all required files are present."""
        required_files = [
            'chat_server.py',
            'chat_interface.html',
            'run_chat.py',
            'src/claude_agent/agent.py'
        ]
        
        for file in required_files:
            self.assertTrue(
                os.path.exists(file),
                f"Required file {file} not found"
            )
    
    def test_run_chat_executable(self):
        """Test that run_chat.py is executable."""
        # Check file permissions
        stat_info = os.stat('run_chat.py')
        # Check if any execute bit is set
        is_executable = bool(stat_info.st_mode & 0o111)
        self.assertTrue(is_executable, "run_chat.py should be executable")


class TestHTMLInterface(unittest.TestCase):
    """Test HTML interface structure."""
    
    def test_html_structure(self):
        """Test that HTML has required elements."""
        with open('chat_interface.html', 'r') as f:
            html_content = f.read()
        
        # Check for required elements
        required_elements = [
            'id="api-key"',
            'id="system-prompt"',
            'id="thinking-budget"',
            'id="max-tokens"',
            'id="message-input"',
            'id="send-btn"',
            'id="connect-btn"',
            'id="mcp-command"',
            'class ChatAPI',
            'class UIState'
        ]
        
        for element in required_elements:
            self.assertIn(element, html_content, f"HTML should contain {element}")
    
    def test_html_javascript(self):
        """Test that HTML contains required JavaScript functionality."""
        with open('chat_interface.html', 'r') as f:
            html_content = f.read()
        
        # Check for API methods
        api_methods = [
            'createSession',
            'sendMessage',
            'connectMCP',
            'disconnectMCP',
            'getMCPStatus'
        ]
        
        for method in api_methods:
            self.assertIn(method, html_content, f"HTML should contain {method} method")


if __name__ == "__main__":
    # Run tests
    print("Running Chat Interface Tests")
    print("=" * 50)
    
    # Check if we're in virtual environment
    if not os.environ.get('VIRTUAL_ENV'):
        print("Warning: Not running in virtual environment")
        print("Some tests may be skipped")
    
    unittest.main(verbosity=2)