"""API request builder for Claude API."""

from typing import Dict, Any, List, Optional


class APIRequestBuilder:
    """Builds API requests for Claude API with extended thinking support."""
    
    def __init__(self, api_key: str, model: str) -> None:
        """
        Initialize the API request builder.
        
        Args:
            api_key: Anthropic API key
            model: Model identifier (e.g., claude-opus-4-20250514)
        """
        self._api_key = api_key
        self._model = model
        self._api_endpoint = "https://api.anthropic.com/v1/messages"
    
    @property
    def api_endpoint(self) -> str:
        """Get the API endpoint URL."""
        return self._api_endpoint
    
    def build_request(
        self,
        system_prompt: str,
        user_prompt: str,
        thinking_budget: Optional[int] = None,
        mcp_context: Optional[str] = None,
        max_tokens: int = 4096,
        stream: bool = True,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Build an API request payload.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            thinking_budget: Optional thinking budget tokens for extended thinking
            mcp_context: Optional MCP context to prepend to user message
            max_tokens: Maximum tokens in response
            stream: Whether to stream the response
            conversation_history: Optional conversation history
            
        Returns:
            Request payload dictionary
            
        Raises:
            ValueError: If parameters are invalid
        """
        # Validate thinking budget if provided
        if thinking_budget is not None:
            if thinking_budget < 1024:
                raise ValueError("budget_tokens must be at least 1024")
            if thinking_budget > 128000:
                raise ValueError("budget_tokens cannot exceed 128000")
            if thinking_budget >= max_tokens:
                raise ValueError("thinking budget must be less than max_tokens")
        
        # Build messages list
        messages = []
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Build user message with optional MCP context
        user_content = user_prompt
        if mcp_context:
            user_content = f"{mcp_context}\n\n{user_prompt}"
        
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        # Build request payload
        request = {
            "model": self._model,
            "system": system_prompt,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        # Add thinking configuration if requested
        if thinking_budget is not None:
            request["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_budget
            }
        
        return request
    
    def get_headers(self, streaming: bool = False) -> Dict[str, str]:
        """
        Get API request headers.
        
        Args:
            streaming: Whether this is a streaming request
            
        Returns:
            Headers dictionary
        """
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        if streaming:
            headers["accept"] = "text/event-stream"
        
        return headers