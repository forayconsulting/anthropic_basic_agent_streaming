"""Claude Agent V2 with fixed MCP support - Complete version."""

from dataclasses import dataclass
from enum import Enum
from typing import AsyncGenerator, Dict, Any, List, Optional
import httpx
import logging

from .sse_parser import SSEParser
from .token_classifier import TokenClassifier
from .mcp_session_manager import MCPSessionManager
from .api_request_builder import APIRequestBuilder

logger = logging.getLogger(__name__)


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
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ClaudeAgentV2:
    """Claude agent with fixed MCP support."""
    
    def __init__(self, api_key: str, model: str = "claude-opus-4-20250514") -> None:
        """Initialize the Claude agent."""
        self._api_key = api_key
        self._model = model
        self._mcp_manager = MCPSessionManager()
        self._request_builder = APIRequestBuilder(api_key, model)
        self._sse_parser = SSEParser()
        self._token_classifier = TokenClassifier()
    
    async def connect_mcp(
        self,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None
    ) -> None:
        """Connect to MCP server."""
        await self._mcp_manager.initialize_connection(command, args, env)
    
    async def disconnect_mcp(self) -> None:
        """Disconnect from MCP server."""
        self._mcp_manager.disconnect()
    
    @property 
    def _mcp_connected(self) -> bool:
        """Check if MCP is connected."""
        return self._mcp_manager.is_connected()
    
    @property
    def _mcp_client(self):
        """Compatibility property for existing code."""
        return self._mcp_manager
    
    async def stream_response(
        self,
        system_prompt: str,
        user_prompt: str,
        thinking_budget: Optional[int] = None,
        max_tokens: int = 4096,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream response from Claude API."""
        # Get MCP context if connected
        mcp_context = None
        if self._mcp_connected:
            mcp_context = self._mcp_manager.get_context()
            logger.debug(f"MCP context: {mcp_context[:200]}..." if mcp_context else "No MCP context")
        
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
                logger.debug(f"HTTP response status: {response.status_code}")
                
                # Check for errors
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield StreamEvent(
                        type=StreamEventType.ERROR,
                        content=f"API Error: {response.status_code} - {error_text.decode()}",
                        metadata={"status_code": response.status_code}
                    )
                    return
                
                # Process SSE stream
                stream_complete = False
                event_count = 0
                
                async for chunk in response.aiter_bytes():
                    # Parse SSE events
                    for sse_event in self._sse_parser.parse(chunk):
                        event_count += 1
                        # Debug log all events
                        logger.debug(f"SSE event #{event_count}: {sse_event.event}, data keys: {list(sse_event.data.keys()) if sse_event.data else 'None'}")
                        
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
                        classified_tokens = list(self._token_classifier.classify(sse_event))
                        logger.debug(f"Classified {len(classified_tokens)} tokens from event")
                        
                        for token in classified_tokens:
                            # Map token type to stream event type
                            event_type = (
                                StreamEventType.THINKING 
                                if token.type.value == "thinking" 
                                else StreamEventType.RESPONSE
                            )
                            
                            logger.debug(f"Yielding {event_type.value} event with content: {repr(token.content[:30])}...")
                            
                            yield StreamEvent(
                                type=event_type,
                                content=token.content,
                                metadata=token.metadata
                            )
                    
                    # Break outer loop if stream is complete
                    if stream_complete:
                        logger.debug("Breaking outer loop - stream complete")
                        break
                
                # After the loop, check if there's any remaining data in the buffer
                logger.debug("Checking for remaining data in SSE parser buffer")
                for sse_event in self._sse_parser.parse(b""):  # Flush buffer
                    logger.debug(f"Final SSE event: {sse_event.event}")
                    
                    # Process any remaining events
                    for token in self._token_classifier.classify(sse_event):
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
                
                logger.debug(f"Stream complete. Total events processed: {event_count}")