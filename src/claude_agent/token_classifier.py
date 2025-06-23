"""Token classification for distinguishing thinking vs response tokens."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Generator, Optional
import logging

from .sse_parser import SSEEvent

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """Types of tokens in Claude's response."""
    THINKING = "thinking"
    RESPONSE = "response"


@dataclass
class ClassifiedToken:
    """A token with its classification and metadata."""
    type: TokenType
    content: str
    metadata: Dict[str, Any]


class TokenClassifier:
    """Classifies tokens from SSE events as thinking or response."""
    
    def __init__(self) -> None:
        """Initialize the token classifier."""
        self._current_block_type: Optional[str] = None
        self._block_index: Optional[int] = None
    
    def classify(self, event: SSEEvent) -> Generator[ClassifiedToken, None, None]:
        """
        Classify tokens from an SSE event.
        
        Args:
            event: SSE event to classify
            
        Yields:
            ClassifiedToken objects
        """
        # Handle content block start events
        if event.event == "content_block_start":
            self._handle_block_start(event)
            
            # Check for thinking summary or redacted thinking
            content_block = event.data.get("content_block", {})
            block_type = content_block.get("type", "")
            
            if block_type == "thinking_summary":
                yield ClassifiedToken(
                    type=TokenType.THINKING,
                    content=content_block.get("summary", ""),
                    metadata={
                        "block_type": "thinking_summary",
                        "block_index": event.data.get("index", 0)
                    }
                )
            elif block_type == "redacted_thinking":
                yield ClassifiedToken(
                    type=TokenType.THINKING,
                    content=content_block.get("text", "[REDACTED]"),
                    metadata={
                        "block_type": "redacted_thinking",
                        "redacted": True,
                        "block_index": event.data.get("index", 0)
                    }
                )
        
        # Handle content block delta events
        elif event.event == "content_block_delta":
            delta = event.data.get("delta", {})
            delta_type = delta.get("type", "")
            
            # Debug what type of delta we're getting
            if self._current_block_type == "thinking":
                logger.debug(f"Thinking delta - type: {delta_type}, delta keys: {list(delta.keys())}")
            
            # Handle both text_delta and thinking_delta
            if delta_type == "text_delta":
                text = delta.get("text", "")
                if text:
                    # Determine token type based on current block
                    token_type = self._get_current_token_type()
                    
                    # Debug logging
                    logger.info(f"Text delta - block type: {self._current_block_type}, text: {repr(text[:50])}")
                    
                    metadata = {
                        "block_index": event.data.get("index", 0),
                        "block_type": self._current_block_type
                    }
                    
                    # Include any additional metadata
                    if "stop_reason" in delta:
                        metadata["stop_reason"] = delta["stop_reason"]
                    
                    yield ClassifiedToken(
                        type=token_type,
                        content=text,
                        metadata=metadata
                    )
            
            elif delta_type == "thinking_delta":
                # Handle thinking deltas which have a different structure
                thinking_text = delta.get("thinking", "")
                if thinking_text:
                    logger.info(f"Thinking delta - text: {repr(thinking_text[:50])}")
                    
                    metadata = {
                        "block_index": event.data.get("index", 0),
                        "block_type": self._current_block_type
                    }
                    
                    yield ClassifiedToken(
                        type=TokenType.THINKING,
                        content=thinking_text,
                        metadata=metadata
                    )
        
        # Handle content block stop events
        elif event.event == "content_block_stop":
            # Reset current block tracking
            self._current_block_type = None
            self._block_index = None
    
    def _handle_block_start(self, event: SSEEvent) -> None:
        """Handle content block start event to track block type."""
        content_block = event.data.get("content_block", {})
        self._current_block_type = content_block.get("type", "text")
        self._block_index = event.data.get("index", 0)
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Content block started - type: {self._current_block_type}, index: {self._block_index}")
    
    def _get_current_token_type(self) -> TokenType:
        """Get token type based on current block type."""
        thinking_types = {"thinking", "thinking_summary", "redacted_thinking"}
        
        if self._current_block_type in thinking_types:
            return TokenType.THINKING
        else:
            return TokenType.RESPONSE
    
    def reset(self) -> None:
        """Reset classifier state for a new message."""
        self._current_block_type = None
        self._block_index = None