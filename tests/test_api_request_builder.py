"""Tests for API request builder."""

import pytest
from typing import Dict, Any

from claude_agent.api_request_builder import APIRequestBuilder


class TestAPIRequestBuilder:
    """Test cases for API request builder."""

    def test_build_basic_request(self):
        """Test building a basic API request."""
        builder = APIRequestBuilder(
            api_key="test_key",
            model="claude-opus-4-20250514"
        )
        
        request = builder.build_request(
            system_prompt="You are a helpful assistant.",
            user_prompt="Hello, how are you?"
        )
        
        assert request["model"] == "claude-opus-4-20250514"
        assert request["system"] == "You are a helpful assistant."
        assert len(request["messages"]) == 1
        assert request["messages"][0]["role"] == "user"
        assert request["messages"][0]["content"] == "Hello, how are you?"
        assert request["stream"] is True  # Default should be streaming

    def test_build_request_with_extended_thinking(self):
        """Test building request with extended thinking enabled."""
        builder = APIRequestBuilder(
            api_key="test_key",
            model="claude-opus-4-20250514"
        )
        
        request = builder.build_request(
            system_prompt="System prompt",
            user_prompt="Complex question",
            thinking_budget=10000,
            max_tokens=20000  # Must be greater than thinking budget
        )
        
        assert "thinking" in request
        assert request["thinking"]["type"] == "enabled"
        assert request["thinking"]["budget_tokens"] == 10000

    def test_build_request_with_mcp_context(self):
        """Test building request with MCP context."""
        builder = APIRequestBuilder(
            api_key="test_key",
            model="claude-opus-4-20250514"
        )
        
        mcp_context = "MCP Tools Available:\n- search: Search tool\n- calculate: Calculator"
        
        request = builder.build_request(
            system_prompt="System prompt",
            user_prompt="Use the search tool to find Python info",
            mcp_context=mcp_context
        )
        
        # MCP context should be prepended to user message
        user_content = request["messages"][0]["content"]
        assert mcp_context in user_content
        assert "Use the search tool to find Python info" in user_content

    def test_build_request_with_custom_max_tokens(self):
        """Test building request with custom max tokens."""
        builder = APIRequestBuilder(
            api_key="test_key",
            model="claude-opus-4-20250514"
        )
        
        request = builder.build_request(
            system_prompt="System prompt",
            user_prompt="User prompt",
            max_tokens=8192
        )
        
        assert request["max_tokens"] == 8192

    def test_build_request_without_streaming(self):
        """Test building request without streaming."""
        builder = APIRequestBuilder(
            api_key="test_key",
            model="claude-opus-4-20250514"
        )
        
        request = builder.build_request(
            system_prompt="System prompt",
            user_prompt="User prompt",
            stream=False
        )
        
        assert request["stream"] is False

    def test_validate_thinking_budget(self):
        """Test validation of thinking budget tokens."""
        builder = APIRequestBuilder(
            api_key="test_key",
            model="claude-opus-4-20250514"
        )
        
        # Test minimum budget
        with pytest.raises(ValueError, match="budget_tokens must be at least 1024"):
            builder.build_request(
                system_prompt="System",
                user_prompt="User",
                thinking_budget=500
            )
        
        # Test maximum budget
        with pytest.raises(ValueError, match="budget_tokens cannot exceed 128000"):
            builder.build_request(
                system_prompt="System",
                user_prompt="User",
                thinking_budget=150000
            )

    def test_thinking_budget_less_than_max_tokens(self):
        """Test that thinking budget is less than max tokens."""
        builder = APIRequestBuilder(
            api_key="test_key",
            model="claude-opus-4-20250514"
        )
        
        with pytest.raises(ValueError, match="thinking budget must be less than max_tokens"):
            builder.build_request(
                system_prompt="System",
                user_prompt="User",
                thinking_budget=5000,
                max_tokens=4000
            )

    def test_get_headers(self):
        """Test getting API headers."""
        builder = APIRequestBuilder(
            api_key="test_key",
            model="claude-opus-4-20250514"
        )
        
        headers = builder.get_headers()
        
        assert headers["x-api-key"] == "test_key"
        assert headers["anthropic-version"] == "2024-06-01"
        assert headers["content-type"] == "application/json"

    def test_get_headers_for_streaming(self):
        """Test getting headers for streaming requests."""
        builder = APIRequestBuilder(
            api_key="test_key",
            model="claude-opus-4-20250514"
        )
        
        headers = builder.get_headers(streaming=True)
        
        assert headers["accept"] == "text/event-stream"

    def test_build_request_with_conversation_history(self):
        """Test building request with conversation history."""
        builder = APIRequestBuilder(
            api_key="test_key",
            model="claude-opus-4-20250514"
        )
        
        history = [
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "2+2 equals 4."}
        ]
        
        request = builder.build_request(
            system_prompt="Math tutor",
            user_prompt="What about 3+3?",
            conversation_history=history
        )
        
        assert len(request["messages"]) == 3
        assert request["messages"][0]["content"] == "What is 2+2?"
        assert request["messages"][1]["content"] == "2+2 equals 4."
        assert request["messages"][2]["content"] == "What about 3+3?"

    def test_api_endpoint(self):
        """Test getting the API endpoint."""
        builder = APIRequestBuilder(
            api_key="test_key",
            model="claude-opus-4-20250514"
        )
        
        assert builder.api_endpoint == "https://api.anthropic.com/v1/messages"

    def test_default_values(self):
        """Test default values in request builder."""
        builder = APIRequestBuilder(
            api_key="test_key",
            model="claude-opus-4-20250514"
        )
        
        request = builder.build_request(
            system_prompt="System",
            user_prompt="User"
        )
        
        assert request["max_tokens"] == 4096  # Default max tokens
        assert request["stream"] is True  # Default streaming
        assert "thinking" not in request  # No thinking by default