"""Claude Agent with fixed tool integration."""

from dataclasses import dataclass
from enum import Enum
from typing import AsyncGenerator, Dict, Any, Optional, List, Tuple
import httpx
import json
import logging

from .sse_parser import SSEParser
from .token_classifier import TokenClassifier, TokenType
from .mcp_client_fixed import MCPConnectionManager
from .mcp_anthropic_bridge import MCPAnthropicBridge, ToolExecutor, AnthropicToolUse
from .api_request_builder import APIRequestBuilder

logger = logging.getLogger(__name__)


class StreamEventType(Enum):
    """Types of streaming events."""
    THINKING = "thinking"
    RESPONSE = "response"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    DONE = "done"


@dataclass
class StreamEvent:
    """Represents a streaming event from the agent."""
    type: StreamEventType
    content: str
    metadata: Optional[Dict[str, Any]] = None


class ClaudeAgentWithToolsFixed:
    """Claude agent with fixed tool integration."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "claude-opus-4-20250514"
    ) -> None:
        """Initialize the agent."""
        self._api_key = api_key
        self._model = model
        self._sse_parser = SSEParser()
        self._token_classifier = TokenClassifier()
        self._mcp_manager = MCPConnectionManager()
        self._request_builder = APIRequestBuilder(api_key, model)
        self._bridge = MCPAnthropicBridge()
    
    @property
    def mcp_manager(self) -> MCPConnectionManager:
        """Get the MCP connection manager."""
        return self._mcp_manager
    
    async def connect_mcp(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None
    ) -> None:
        """Connect to an MCP server."""
        await self._mcp_manager.connect(command, args, env, cwd)
        logger.info(f"Connected to MCP server with {len(self._mcp_manager.tools)} tools")
    
    async def disconnect_mcp(self) -> None:
        """Disconnect from MCP server."""
        await self._mcp_manager.disconnect()
        logger.info("Disconnected from MCP server")
    
    async def stream_response_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        thinking_budget: Optional[int] = None,
        max_tokens: int = 4096,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream response from Claude with automatic tool handling."""
        
        # Get available tools if MCP is connected
        tools = []
        if self._mcp_manager.is_connected:
            tools = self._mcp_manager.get_anthropic_tools()
            logger.info(f"Including {len(tools)} MCP tools in request")
        
        # Build initial request
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({
            "role": "user",
            "content": user_prompt
        })
        
        # Keep track of the conversation
        current_messages = messages.copy()
        
        # Tool use cycle
        max_rounds = 5
        round_num = 0
        
        while round_num < max_rounds:
            round_num += 1
            
            # Make API request
            request_data = {
                "model": self._model,
                "system": system_prompt,
                "messages": current_messages,
                "max_tokens": max_tokens,
                "stream": True
            }
            
            # Add tools if available
            if tools:
                request_data["tools"] = tools
            
            # Add thinking configuration if requested
            if thinking_budget is not None:
                request_data["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": thinking_budget
                }
            
            headers = self._request_builder.get_headers(streaming=True)
            
            # Track state for parsing
            current_block_type = None
            current_block_id = None
            current_tool_name = None
            current_tool_input_text = ""
            response_content = []
            tool_uses = []
            stop_reason = None
            
            try:
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        'POST',
                        self._request_builder.api_endpoint,
                        json=request_data,
                        headers=headers,
                        timeout=httpx.Timeout(300.0)
                    ) as response:
                        response.raise_for_status()
                        
                        async for chunk in response.aiter_bytes():
                            for sse_event in self._sse_parser.parse(chunk):
                                
                                if sse_event.event == "content_block_start":
                                    # Track the type of content block starting
                                    block_data = sse_event.data
                                    current_block_type = block_data.get("content_block", {}).get("type")
                                    current_block_id = block_data.get("content_block", {}).get("id")
                                    
                                    if current_block_type == "tool_use":
                                        current_tool_name = block_data.get("content_block", {}).get("name")
                                        current_tool_input_text = ""
                                        yield StreamEvent(
                                            type=StreamEventType.TOOL_USE,
                                            content=f"Calling tool: {current_tool_name}",
                                            metadata={"tool_name": current_tool_name}
                                        )
                                
                                elif sse_event.event == "content_block_delta":
                                    delta_data = sse_event.data.get("delta", {})
                                    
                                    if current_block_type == "text":
                                        # Text content
                                        text = delta_data.get("text", "")
                                        if text:
                                            response_content.append(text)
                                            yield StreamEvent(
                                                type=StreamEventType.RESPONSE,
                                                content=text
                                            )
                                    
                                    elif current_block_type == "tool_use":
                                        # Tool input streaming
                                        input_json = delta_data.get("partial_json", "")
                                        if input_json:
                                            current_tool_input_text += input_json
                                
                                elif sse_event.event == "content_block_stop":
                                    if current_block_type == "tool_use" and current_tool_name:
                                        # Parse the complete tool input
                                        try:
                                            tool_input = json.loads(current_tool_input_text)
                                        except:
                                            tool_input = {}
                                        
                                        tool_uses.append(AnthropicToolUse(
                                            id=current_block_id,
                                            name=current_tool_name,
                                            input=tool_input
                                        ))
                                    
                                    # Reset block tracking
                                    current_block_type = None
                                    current_block_id = None
                                    current_tool_name = None
                                    current_tool_input_text = ""
                                
                                elif sse_event.event == "message_delta":
                                    # Check stop reason
                                    delta = sse_event.data.get("delta", {})
                                    stop_reason = delta.get("stop_reason")
                                
                                elif sse_event.event == "message_stop":
                                    # Message complete
                                    pass
            
            except Exception as e:
                yield StreamEvent(
                    type=StreamEventType.ERROR,
                    content=str(e),
                    metadata={"error_type": type(e).__name__}
                )
                return
            
            # Build assistant message
            content_blocks = []
            
            # Add text content if any
            if response_content:
                content_blocks.append({
                    "type": "text",
                    "text": "".join(response_content)
                })
            
            # Add tool use blocks
            for tool_use in tool_uses:
                content_blocks.append({
                    "type": "tool_use",
                    "id": tool_use.id,
                    "name": tool_use.name,
                    "input": tool_use.input
                })
            
            # Add assistant message
            assistant_message = {
                "role": "assistant",
                "content": content_blocks if content_blocks else "".join(response_content)
            }
            current_messages.append(assistant_message)
            
            # If Claude used tools, execute them
            if stop_reason == "tool_use" and tool_uses:
                logger.info(f"Claude requested {len(tool_uses)} tool uses")
                
                # Execute tools
                tool_results = []
                executor = ToolExecutor(self._mcp_manager)
                
                for tool_use in tool_uses:
                    # Find tool schema
                    tool_schema = None
                    for tool in tools:
                        if tool["name"] == tool_use.name:
                            tool_schema = tool.get("input_schema", {})
                            break
                    
                    # Execute tool
                    result = await executor.execute_tool(tool_use, tool_schema)
                    tool_results.append(result)
                    
                    yield StreamEvent(
                        type=StreamEventType.TOOL_RESULT,
                        content=f"Tool result received",
                        metadata={
                            "tool_use_id": result.tool_use_id,
                            "tool_name": tool_use.name,
                            "is_error": result.is_error,
                            "preview": result.content[:100] + "..." if len(result.content) > 100 else result.content
                        }
                    )
                
                # Add tool results to conversation
                tool_result_message = self._bridge.format_tool_response_message(tool_results)
                current_messages.append(tool_result_message)
                
                # Reset for next iteration
                response_content = []
                tool_uses = []
                
            else:
                # No more tool uses, we're done
                break
        
        yield StreamEvent(type=StreamEventType.DONE, content="")