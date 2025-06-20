"""SSE (Server-Sent Events) parser for Claude API streaming responses."""

from dataclasses import dataclass
from typing import Dict, Any, List, Generator, Optional
import json


@dataclass
class SSEEvent:
    """Represents a parsed SSE event."""
    event: str
    data: Dict[str, Any]


class SSEParser:
    """Parser for Server-Sent Events from Claude API."""
    
    def __init__(self) -> None:
        """Initialize the SSE parser."""
        self._buffer = b""
    
    def parse(self, chunk: bytes) -> Generator[SSEEvent, None, None]:
        """
        Parse SSE events from a chunk of bytes.
        
        Args:
            chunk: Raw bytes from the SSE stream
            
        Yields:
            SSEEvent objects for each complete event
        """
        # Add chunk to buffer
        self._buffer += chunk
        
        # Split by double newline (event separator)
        while b"\n\n" in self._buffer:
            # Find the end of the current event
            event_end = self._buffer.index(b"\n\n")
            event_data = self._buffer[:event_end]
            
            # Remove processed event from buffer
            self._buffer = self._buffer[event_end + 2:]
            
            # Skip empty events
            if not event_data:
                continue
            
            # Parse the event
            event = self._parse_event(event_data)
            if event:
                yield event
    
    def _parse_event(self, event_data: bytes) -> Optional[SSEEvent]:
        """
        Parse a single SSE event.
        
        Args:
            event_data: Raw bytes of a single event
            
        Returns:
            SSEEvent object or None if parsing fails
        """
        lines = event_data.decode('utf-8').strip().split('\n')
        event_type = None
        data_lines = []
        
        for line in lines:
            if line.startswith('event: '):
                event_type = line[7:]  # Remove 'event: ' prefix
            elif line.startswith('data: '):
                data_lines.append(line[6:])  # Remove 'data: ' prefix
        
        if not event_type or not data_lines:
            return None
        
        # Join data lines and parse JSON
        try:
            data = json.loads(''.join(data_lines))
            return SSEEvent(event=event_type, data=data)
        except json.JSONDecodeError:
            return None