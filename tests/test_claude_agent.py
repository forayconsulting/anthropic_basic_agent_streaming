"""Integration tests for Claude Agent."""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from types import SimpleNamespace
import asyncio
from typing import AsyncGenerator, List, Dict, Any

from claude_agent.agent import ClaudeAgent, StreamEvent, StreamEventType


class TestClaudeAgent:
    """Integration tests for Claude Agent."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initialization with API key."""
        agent = ClaudeAgent(api_key="test_key")
        
        assert agent._api_key == "test_key"
        assert agent._model == "claude-opus-4-20250514"  # Default model
        assert not agent._mcp_connected

    @pytest.mark.asyncio
    async def test_agent_with_custom_model(self):
        """Test agent initialization with custom model."""
        agent = ClaudeAgent(api_key="test_key", model="claude-3-opus-20240229")
        
        assert agent._model == "claude-3-opus-20240229"

    @pytest.mark.asyncio
    async def test_connect_mcp_server(self):
        """Test connecting to MCP server."""
        agent = ClaudeAgent(api_key="test_key")
        
        with patch.object(agent._mcp_client, 'connect_stdio') as mock_connect:
            await agent.connect_mcp("python", ["-m", "my_server"])
            
            mock_connect.assert_called_once_with("python", ["-m", "my_server"], None)
            assert agent._mcp_connected

    @pytest.mark.asyncio
    async def test_stream_response_without_mcp(self):
        """Test streaming response without MCP context."""
        agent = ClaudeAgent(api_key="test_key")
        
        # Mock httpx response
        mock_response = self._create_mock_response([
            b'event: message_start\ndata: {"type": "message_start", "message": {"id": "msg_123"}}\n\n',
            b'event: content_block_start\ndata: {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}\n\n',
            b'event: content_block_delta\ndata: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello"}}\n\n',
            b'event: content_block_delta\ndata: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": " world!"}}\n\n',
            b'event: message_stop\ndata: {"type": "message_stop"}\n\n'
        ])
        
        with patch('httpx.AsyncClient.stream') as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response
            events = []
            async for event in agent.stream_response("System", "User"):
                events.append(event)
        
        # Verify events
        assert len(events) == 2  # Two text deltas
        assert events[0].type == StreamEventType.RESPONSE
        assert events[0].content == "Hello"
        assert events[1].type == StreamEventType.RESPONSE
        assert events[1].content == " world!"

    @pytest.mark.asyncio
    async def test_stream_response_with_thinking(self):
        """Test streaming response with extended thinking."""
        agent = ClaudeAgent(api_key="test_key")
        
        # Mock httpx response with thinking
        mock_response = self._create_mock_response([
            b'event: message_start\ndata: {"type": "message_start", "message": {"id": "msg_123"}}\n\n',
            b'event: content_block_start\ndata: {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking_summary", "summary": "Analyzing the request..."}}\n\n',
            b'event: content_block_start\ndata: {"type": "content_block_start", "index": 1, "content_block": {"type": "text", "text": ""}}\n\n',
            b'event: content_block_delta\ndata: {"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": "Based on my analysis"}}\n\n',
            b'event: message_stop\ndata: {"type": "message_stop"}\n\n'
        ])
        
        with patch('httpx.AsyncClient.stream') as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response
            events = []
            async for event in agent.stream_response("System", "User", thinking_budget=5000, max_tokens=10000):
                events.append(event)
        
        # Verify thinking and response events
        assert len(events) == 2
        assert events[0].type == StreamEventType.THINKING
        assert events[0].content == "Analyzing the request..."
        assert events[1].type == StreamEventType.RESPONSE
        assert events[1].content == "Based on my analysis"

    @pytest.mark.asyncio
    async def test_stream_response_with_mcp_context(self):
        """Test streaming response with MCP context."""
        agent = ClaudeAgent(api_key="test_key")
        agent._mcp_connected = True
        
        # Mock MCP context
        with patch.object(agent._mcp_client, 'get_context', return_value="MCP Tools: search, calculate"):
            # Mock httpx response
            mock_response = self._create_mock_response([
                b'event: message_start\ndata: {"type": "message_start"}\n\n',
                b'event: content_block_start\ndata: {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}}\n\n',
                b'event: content_block_delta\ndata: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Using search tool"}}\n\n',
                b'event: message_stop\ndata: {"type": "message_stop"}\n\n'
            ])
            
            with patch('httpx.AsyncClient.stream') as mock_stream:
                mock_stream.return_value.__aenter__.return_value = mock_response
                events = []
                async for event in agent.stream_response("System", "Search for Python"):
                    events.append(event)
                
                # Verify MCP context was included in request
                call_args = mock_stream.call_args
                # stream() takes: method, url, json=..., headers=..., timeout=...
                request_data = call_args.kwargs['json']
                user_content = request_data['messages'][0]['content']
                assert "MCP Tools: search, calculate" in user_content
                assert "Search for Python" in user_content

    @pytest.mark.asyncio
    async def test_handle_error_event(self):
        """Test handling error events from API."""
        agent = ClaudeAgent(api_key="test_key")
        
        # Mock error response
        mock_response = self._create_mock_response([
            b'event: error\ndata: {"type": "error", "error": {"type": "invalid_request_error", "message": "Invalid API key"}}\n\n'
        ])
        
        with patch('httpx.AsyncClient.stream') as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response
            events = []
            async for event in agent.stream_response("System", "User"):
                events.append(event)
            
            assert len(events) == 1
            assert events[0].type == StreamEventType.ERROR
            assert "Invalid API key" in events[0].content

    @pytest.mark.asyncio
    async def test_disconnect_mcp(self):
        """Test disconnecting from MCP server."""
        agent = ClaudeAgent(api_key="test_key")
        agent._mcp_connected = True
        
        with patch.object(agent._mcp_client, 'disconnect') as mock_disconnect:
            await agent.disconnect_mcp()
            
            mock_disconnect.assert_called_once()
            assert not agent._mcp_connected

    @pytest.mark.asyncio
    async def test_conversation_history(self):
        """Test streaming with conversation history."""
        agent = ClaudeAgent(api_key="test_key")
        
        history = [
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "4"}
        ]
        
        mock_response = self._create_mock_response([
            b'event: message_start\ndata: {"type": "message_start"}\n\n',
            b'event: content_block_start\ndata: {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}}\n\n',
            b'event: content_block_delta\ndata: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "3+3 is 6"}}\n\n',
            b'event: message_stop\ndata: {"type": "message_stop"}\n\n'
        ])
        
        with patch('httpx.AsyncClient.stream') as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response
            events = []
            async for event in agent.stream_response("Math tutor", "What about 3+3?", conversation_history=history):
                events.append(event)
            
            # Verify history was included
            call_args = mock_stream.call_args
            request_data = call_args[1]['json']
            assert len(request_data['messages']) == 3
            assert request_data['messages'][0]['content'] == "What is 2+2?"
            assert request_data['messages'][1]['content'] == "4"
            assert request_data['messages'][2]['content'] == "What about 3+3?"

    @pytest.mark.asyncio
    async def test_custom_headers(self):
        """Test that proper headers are sent."""
        agent = ClaudeAgent(api_key="test_key")
        
        mock_response = self._create_mock_response([
            b'event: message_stop\ndata: {"type": "message_stop"}\n\n'
        ])
        
        with patch('httpx.AsyncClient.stream') as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response
            async for _ in agent.stream_response("System", "User"):
                pass
            
            # Verify headers
            call_args = mock_stream.call_args
            headers = call_args.kwargs['headers']
            assert headers['x-api-key'] == "test_key"
            assert headers['accept'] == "text/event-stream"
            assert headers['content-type'] == "application/json"

    @pytest.mark.asyncio
    async def test_max_tokens_configuration(self):
        """Test configuring max tokens."""
        agent = ClaudeAgent(api_key="test_key")
        
        mock_response = self._create_mock_response([
            b'event: message_stop\ndata: {"type": "message_stop"}\n\n'
        ])
        
        with patch('httpx.AsyncClient.stream') as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response
            async for _ in agent.stream_response("System", "User", max_tokens=8192):
                pass
            
            # Verify max tokens in request
            call_args = mock_stream.call_args
            request_data = call_args[1]['json']
            assert request_data['max_tokens'] == 8192

    async def _create_mock_sse_stream(self, chunks: List[bytes]) -> AsyncGenerator[bytes, None]:
        """Helper to create mock SSE stream."""
        for chunk in chunks:
            yield chunk
    
    def _create_mock_response(self, chunks: List[bytes]) -> AsyncMock:
        """Create a mock response with proper aiter_bytes."""
        mock_response = AsyncMock()
        mock_response.aiter_bytes = lambda: self._create_mock_sse_stream(chunks)
        return mock_response