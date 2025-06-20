"""Tests for token classification logic."""

import pytest
from typing import List

from claude_agent.token_classifier import TokenClassifier, TokenType, ClassifiedToken
from claude_agent.sse_parser import SSEEvent


class TestTokenClassifier:
    """Test cases for token classification."""

    def test_classify_thinking_summary(self):
        """Test classification of thinking summary tokens."""
        classifier = TokenClassifier()
        event = SSEEvent(
            event="content_block_start",
            data={
                "type": "content_block_start",
                "index": 0,
                "content_block": {
                    "type": "thinking_summary",
                    "summary": "The model analyzed the problem..."
                }
            }
        )
        
        tokens = list(classifier.classify(event))
        
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.THINKING
        assert tokens[0].content == "The model analyzed the problem..."
        assert tokens[0].metadata["block_type"] == "thinking_summary"

    def test_classify_text_response(self):
        """Test classification of regular text response tokens."""
        classifier = TokenClassifier()
        event = SSEEvent(
            event="content_block_delta",
            data={
                "type": "content_block_delta",
                "index": 0,
                "delta": {
                    "type": "text_delta",
                    "text": "Hello, how can I help you?"
                }
            }
        )
        
        tokens = list(classifier.classify(event))
        
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.RESPONSE
        assert tokens[0].content == "Hello, how can I help you?"
        assert tokens[0].metadata.get("block_index") == 0

    def test_classify_with_active_thinking_block(self):
        """Test classification when thinking block is active."""
        classifier = TokenClassifier()
        
        # Start a thinking block
        start_event = SSEEvent(
            event="content_block_start",
            data={
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "thinking", "text": ""}
            }
        )
        list(classifier.classify(start_event))
        
        # Text delta should be classified as thinking
        delta_event = SSEEvent(
            event="content_block_delta",
            data={
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "Let me think about this..."}
            }
        )
        
        tokens = list(classifier.classify(delta_event))
        
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.THINKING
        assert tokens[0].content == "Let me think about this..."

    def test_classify_block_transitions(self):
        """Test proper classification during block transitions."""
        classifier = TokenClassifier()
        
        # Start thinking block
        thinking_start = SSEEvent(
            event="content_block_start",
            data={
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "thinking", "text": ""}
            }
        )
        list(classifier.classify(thinking_start))
        
        # Thinking text
        thinking_delta = SSEEvent(
            event="content_block_delta",
            data={
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "Analyzing..."}
            }
        )
        tokens1 = list(classifier.classify(thinking_delta))
        assert tokens1[0].type == TokenType.THINKING
        
        # End thinking block
        thinking_stop = SSEEvent(
            event="content_block_stop",
            data={"type": "content_block_stop", "index": 0}
        )
        list(classifier.classify(thinking_stop))
        
        # Start response block
        response_start = SSEEvent(
            event="content_block_start",
            data={
                "type": "content_block_start",
                "index": 1,
                "content_block": {"type": "text", "text": ""}
            }
        )
        list(classifier.classify(response_start))
        
        # Response text
        response_delta = SSEEvent(
            event="content_block_delta",
            data={
                "type": "content_block_delta",
                "index": 1,
                "delta": {"type": "text_delta", "text": "Here's my answer:"}
            }
        )
        tokens2 = list(classifier.classify(response_delta))
        assert tokens2[0].type == TokenType.RESPONSE

    def test_ignore_non_content_events(self):
        """Test that non-content events are ignored."""
        classifier = TokenClassifier()
        
        # Message start event
        event1 = SSEEvent(
            event="message_start",
            data={"type": "message_start", "message": {"id": "msg_123"}}
        )
        tokens1 = list(classifier.classify(event1))
        assert len(tokens1) == 0
        
        # Ping event
        event2 = SSEEvent(
            event="ping",
            data={"type": "ping"}
        )
        tokens2 = list(classifier.classify(event2))
        assert len(tokens2) == 0

    def test_handle_redacted_thinking(self):
        """Test handling of redacted thinking blocks."""
        classifier = TokenClassifier()
        event = SSEEvent(
            event="content_block_start",
            data={
                "type": "content_block_start",
                "index": 0,
                "content_block": {
                    "type": "redacted_thinking",
                    "text": "[REDACTED]"
                }
            }
        )
        
        tokens = list(classifier.classify(event))
        
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.THINKING
        assert tokens[0].content == "[REDACTED]"
        assert tokens[0].metadata["redacted"] is True

    def test_reset_classifier_state(self):
        """Test resetting classifier state between messages."""
        classifier = TokenClassifier()
        
        # Set up thinking state
        start_event = SSEEvent(
            event="content_block_start",
            data={
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "thinking", "text": ""}
            }
        )
        list(classifier.classify(start_event))
        
        # Reset state
        classifier.reset()
        
        # New text should be response (not thinking)
        delta_event = SSEEvent(
            event="content_block_delta",
            data={
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "New message"}
            }
        )
        tokens = list(classifier.classify(delta_event))
        
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.RESPONSE

    def test_preserve_metadata(self):
        """Test that relevant metadata is preserved in classified tokens."""
        classifier = TokenClassifier()
        event = SSEEvent(
            event="content_block_delta",
            data={
                "type": "content_block_delta",
                "index": 2,
                "delta": {
                    "type": "text_delta",
                    "text": "Test content",
                    "stop_reason": "max_tokens"
                }
            }
        )
        
        tokens = list(classifier.classify(event))
        
        assert len(tokens) == 1
        assert tokens[0].metadata["block_index"] == 2
        assert tokens[0].metadata.get("stop_reason") == "max_tokens"