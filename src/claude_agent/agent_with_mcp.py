"""Claude Agent with real MCP integration."""

from dataclasses import dataclass
from enum import Enum
from typing import AsyncGenerator, Dict, Any, Optional, List
import httpx

from .sse_parser import SSEParser
from .token_classifier import TokenClassifier, TokenType
from .mcp_client_working import WorkingMCPClient
from .api_request_builder import APIRequestBuilder


class StreamEventType(Enum):
    """Types of streaming events."""
    THINKING = "thinking"
    RESPONSE = "response"
    ERROR = "error"
    DONE = "done"


@dataclass
class StreamEvent:
    """Represents a streaming event from the agent."""
    type: StreamEventType
    content: str
    metadata: Optional[Dict[str, Any]] = None


class ClaudeAgentWithMCP:
    """Claude agent with real MCP integration and streaming support."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "claude-opus-4-20250514"
    ) -> None:
        """
        Initialize the agent.
        
        Args:
            api_key: Anthropic API key
            model: Model identifier
        """
        self._api_key = api_key
        self._model = model
        self._sse_parser = SSEParser()
        self._token_classifier = TokenClassifier()
        self._mcp_client = WorkingMCPClient()
        self._request_builder = APIRequestBuilder(api_key, model)
    
    @property
    def mcp_client(self) -> WorkingMCPClient:
        """Get the MCP client instance."""
        return self._mcp_client
    
    async def connect_mcp(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None
    ) -> None:
        """
        Connect to an MCP server.
        
        Args:
            command: Command to run the MCP server
            args: Arguments for the command
            env: Optional environment variables
            cwd: Optional working directory
        """
        await self._mcp_client.connect_stdio(command, args, env, cwd)
    
    async def disconnect_mcp(self) -> None:
        """Disconnect from MCP server."""
        await self._mcp_client.disconnect()
    
    async def stream_response(
        self,
        system_prompt: str,
        user_prompt: str,
        thinking_budget: Optional[int] = None,
        include_mcp_context: bool = True,
        max_tokens: int = 4096,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream response from Claude API.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            thinking_budget: Optional thinking budget tokens
            include_mcp_context: Whether to include MCP context
            max_tokens: Maximum tokens in response
            conversation_history: Optional conversation history
            
        Yields:
            StreamEvent objects
        """
        # Get MCP context if connected and requested
        mcp_context = None
        if include_mcp_context and self._mcp_client.is_connected:
            mcp_context = await self._mcp_client.get_context()
        
        # Build request
        request = self._request_builder.build_request(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            thinking_budget=thinking_budget,
            mcp_context=mcp_context,
            max_tokens=max_tokens,
            stream=True,
            conversation_history=conversation_history
        )
        
        headers = self._request_builder.get_headers(streaming=True)
        
        # Stream response
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    'POST',
                    self._request_builder.api_endpoint,
                    json=request,
                    headers=headers,
                    timeout=httpx.Timeout(300.0)
                ) as response:
                    response.raise_for_status()
                    
                    async for chunk in response.aiter_bytes():
                        for sse_event in self._sse_parser.parse(chunk):
                            for token in self._token_classifier.classify(sse_event):
                                # Map token type to stream event type
                                if token.type == TokenType.THINKING:
                                    event_type = StreamEventType.THINKING
                                else:
                                    event_type = StreamEventType.RESPONSE
                                
                                yield StreamEvent(
                                    type=event_type,
                                    content=token.content,
                                    metadata=token.metadata
                                )
                    
                    yield StreamEvent(type=StreamEventType.DONE, content="")
                    
        except Exception as e:
            yield StreamEvent(
                type=StreamEventType.ERROR,
                content=str(e),
                metadata={"error_type": type(e).__name__}
            )
    
    async def call_mcp_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        system_prompt: str = "You are a helpful assistant.",
        result_prompt: str = "Based on the tool result above, please provide a helpful response."
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Call an MCP tool and stream Claude's interpretation of the result.
        
        Args:
            tool_name: Name of the MCP tool to call
            arguments: Arguments for the tool
            system_prompt: System prompt for Claude
            result_prompt: Prompt to ask Claude about the result
            
        Yields:
            StreamEvent objects
        """
        if not self._mcp_client.is_connected:
            yield StreamEvent(
                type=StreamEventType.ERROR,
                content="MCP client not connected",
                metadata={"error_type": "NotConnected"}
            )
            return
        
        try:
            # Call the MCP tool
            tool_result = await self._mcp_client.call_tool(tool_name, arguments)
            
            # Build prompt with tool result
            user_prompt = f"Tool '{tool_name}' returned:\n\n{tool_result}\n\n{result_prompt}"
            
            # Stream Claude's response about the tool result
            async for event in self.stream_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                include_mcp_context=False  # Don't include full context again
            ):
                yield event
                
        except Exception as e:
            yield StreamEvent(
                type=StreamEventType.ERROR,
                content=f"Error calling MCP tool: {str(e)}",
                metadata={"error_type": type(e).__name__, "tool": tool_name}
            )