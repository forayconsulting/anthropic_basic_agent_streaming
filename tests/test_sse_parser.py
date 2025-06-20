"""Tests for SSE event parser."""

import pytest
from typing import List, Dict, Any

from claude_agent.sse_parser import SSEParser, SSEEvent


class TestSSEParser:
    """Test cases for SSE event parsing."""

    def test_parse_simple_event(self):
        """Test parsing a simple SSE event."""
        parser = SSEParser()
        raw_event = b"event: message\ndata: {\"type\": \"ping\"}\n\n"
        
        events = list(parser.parse(raw_event))
        
        assert len(events) == 1
        assert events[0].event == "message"
        assert events[0].data == {"type": "ping"}

    def test_parse_message_start_event(self):
        """Test parsing a message_start event from Claude API."""
        parser = SSEParser()
        raw_event = b'event: message_start\ndata: {"type": "message_start", "message": {"id": "msg_123", "type": "message", "role": "assistant", "content": [], "model": "claude-opus-4-20250514", "usage": {"input_tokens": 25, "output_tokens": 0}}}\n\n'
        
        events = list(parser.parse(raw_event))
        
        assert len(events) == 1
        assert events[0].event == "message_start"
        assert events[0].data["type"] == "message_start"
        assert events[0].data["message"]["id"] == "msg_123"
        assert events[0].data["message"]["model"] == "claude-opus-4-20250514"

    def test_parse_content_block_delta(self):
        """Test parsing content block delta events."""
        parser = SSEParser()
        raw_event = b'event: content_block_delta\ndata: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello, "}}\n\n'
        
        events = list(parser.parse(raw_event))
        
        assert len(events) == 1
        assert events[0].event == "content_block_delta"
        assert events[0].data["delta"]["text"] == "Hello, "

    def test_parse_multiple_events(self):
        """Test parsing multiple SSE events in a single chunk."""
        parser = SSEParser()
        raw_events = (
            b'event: message_start\ndata: {"type": "message_start", "message": {"id": "msg_123"}}\n\n'
            b'event: content_block_start\ndata: {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}\n\n'
            b'event: content_block_delta\ndata: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello"}}\n\n'
        )
        
        events = list(parser.parse(raw_events))
        
        assert len(events) == 3
        assert events[0].event == "message_start"
        assert events[1].event == "content_block_start"
        assert events[2].event == "content_block_delta"
        assert events[2].data["delta"]["text"] == "Hello"

    def test_parse_thinking_summary_event(self):
        """Test parsing thinking summary events for extended thinking mode."""
        parser = SSEParser()
        raw_event = b'event: content_block_start\ndata: {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking_summary", "summary": "The model considered various approaches..."}}\n\n'
        
        events = list(parser.parse(raw_event))
        
        assert len(events) == 1
        assert events[0].event == "content_block_start"
        assert events[0].data["content_block"]["type"] == "thinking_summary"
        assert "considered various approaches" in events[0].data["content_block"]["summary"]

    def test_handle_incomplete_event(self):
        """Test handling incomplete SSE events (buffering)."""
        parser = SSEParser()
        
        # First chunk - incomplete
        chunk1 = b'event: content_block_delta\ndata: {"type": "content_block_'
        events1 = list(parser.parse(chunk1))
        assert len(events1) == 0  # Should buffer incomplete event
        
        # Second chunk - completes the event
        chunk2 = b'delta", "index": 0, "delta": {"type": "text_delta", "text": "world"}}\n\n'
        events2 = list(parser.parse(chunk2))
        assert len(events2) == 1
        assert events2[0].data["delta"]["text"] == "world"

    def test_parse_error_event(self):
        """Test parsing error events."""
        parser = SSEParser()
        raw_event = b'event: error\ndata: {"type": "error", "error": {"type": "invalid_request_error", "message": "Invalid API key"}}\n\n'
        
        events = list(parser.parse(raw_event))
        
        assert len(events) == 1
        assert events[0].event == "error"
        assert events[0].data["error"]["type"] == "invalid_request_error"

    def test_parse_ping_event(self):
        """Test parsing ping events (keepalive)."""
        parser = SSEParser()
        raw_event = b'event: ping\ndata: {"type": "ping"}\n\n'
        
        events = list(parser.parse(raw_event))
        
        assert len(events) == 1
        assert events[0].event == "ping"
        assert events[0].data["type"] == "ping"

    def test_parse_message_stop_event(self):
        """Test parsing message stop event."""
        parser = SSEParser()
        raw_event = b'event: message_stop\ndata: {"type": "message_stop"}\n\n'
        
        events = list(parser.parse(raw_event))
        
        assert len(events) == 1
        assert events[0].event == "message_stop"
        assert events[0].data["type"] == "message_stop"

    @pytest.mark.asyncio
    async def test_async_parse_stream(self):
        """Test async parsing of SSE stream."""
        parser = SSEParser()
        
        async def mock_stream():
            """Mock async stream of SSE events."""
            yield b'event: message_start\ndata: {"type": "message_start"}\n\n'
            yield b'event: content_block_delta\ndata: {"type": "content_block_delta", "delta": {"text": "Hi"}}\n\n'
            yield b'event: message_stop\ndata: {"type": "message_stop"}\n\n'
        
        events = []
        async for chunk in mock_stream():
            events.extend(parser.parse(chunk))
        
        assert len(events) == 3
        assert events[0].event == "message_start"
        assert events[1].event == "content_block_delta"
        assert events[2].event == "message_stop"