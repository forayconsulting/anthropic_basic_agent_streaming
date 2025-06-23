"""Claude Agent - Main orchestration layer."""

from dataclasses import dataclass
from enum import Enum
from typing import AsyncGenerator, Dict, Any, List, Optional
import httpx
import logging

from .sse_parser import SSEParser
from .token_classifier import TokenClassifier
from .mcp_client import MCPClientWrapper
from .api_request_builder import APIRequestBuilder

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class StreamEventType(Enum):
    """Types of events in the stream."""
    THINKING = "thinking"
    RESPONSE = "response"
    ERROR = "error"


@dataclass
class StreamEvent:
    """Event emitted during streaming."""
    type: StreamEventType
    content: str
    metadata: Dict[str, Any]


class ClaudeAgent:
    """Main Claude agent orchestrating all components."""
    
    def __init__(self, api_key: str, model: str = "claude-opus-4-20250514") -> None:
        """
        Initialize the Claude agent.
        
        Args:
            api_key: Anthropic API key
            model: Model identifier
        """
        self._api_key = api_key
        self._model = model
        self._mcp_client = MCPClientWrapper()
        self._mcp_connected = False
        self._request_builder = APIRequestBuilder(api_key, model)
        self._sse_parser = SSEParser()
        self._token_classifier = TokenClassifier()
    
    async def connect_mcp(
        self,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Connect to MCP server.
        
        Args:
            command: Command to run MCP server
            args: Command arguments
            env: Optional environment variables
        """
        await self._mcp_client.connect_stdio(command, args, env)
        self._mcp_connected = True
    
    async def disconnect_mcp(self) -> None:
        """Disconnect from MCP server."""
        if self._mcp_connected:
            await self._mcp_client.disconnect()
            self._mcp_connected = False
    
    async def stream_response(
        self,
        system_prompt: str,
        user_prompt: str,
        thinking_budget: Optional[int] = None,
        max_tokens: int = 4096,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream response from Claude API.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            thinking_budget: Optional thinking budget for extended thinking
            max_tokens: Maximum response tokens
            conversation_history: Optional conversation history
            
        Yields:
            StreamEvent objects
        """
        # Get MCP context if connected
        mcp_context = None
        if self._mcp_connected:
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
        
        # Get headers
        headers = self._request_builder.get_headers(streaming=True)
        
        # Reset token classifier for new message
        self._token_classifier.reset()
        
        # Make streaming request
        async with httpx.AsyncClient() as client:
            async with client.stream(
                'POST',
                self._request_builder.api_endpoint,
                json=request,
                headers=headers,
                timeout=httpx.Timeout(300.0)  # 5 minute timeout
            ) as response:
                # Process SSE stream
                stream_complete = False
                async for chunk in response.aiter_bytes():
                    # Parse SSE events
                    for sse_event in self._sse_parser.parse(chunk):
                        # Debug log all events
                        logger.info(f"SSE event: {sse_event.event}, data keys: {list(sse_event.data.keys()) if sse_event.data else 'None'}")
                        
                        # Handle error events
                        if sse_event.event == "error":
                            error_msg = sse_event.data.get("error", {}).get("message", "Unknown error")
                            yield StreamEvent(
                                type=StreamEventType.ERROR,
                                content=error_msg,
                                metadata=sse_event.data
                            )
                            continue
                        
                        # Handle message stop event - signals end of message
                        if sse_event.event == "message_stop":
                            logger.debug("Received message_stop event - stream complete")
                            stream_complete = True
                            break
                        
                        # Skip ping events (keepalive)
                        if sse_event.event == "ping":
                            logger.debug("Received ping event")
                            continue
                        
                        # Classify tokens
                        for token in self._token_classifier.classify(sse_event):
                            # Map token type to stream event type
                            event_type = (
                                StreamEventType.THINKING 
                                if token.type.value == "thinking" 
                                else StreamEventType.RESPONSE
                            )
                            
                            yield StreamEvent(
                                type=event_type,
                                content=token.content,
                                metadata=token.metadata
                            )
                    
                    # Break outer loop if stream is complete
                    if stream_complete:
                        logger.info("Breaking outer loop - stream complete")
                        break
                
                # After the loop, check if there's any remaining data in the buffer
                logger.info("Checking for remaining data in SSE parser buffer")
                for sse_event in self._sse_parser.parse(b""):  # Flush buffer
                    logger.info(f"Final SSE event: {sse_event.event}")
                    if sse_event.event == "message_stop":
                        logger.info("Found message_stop in final buffer flush")