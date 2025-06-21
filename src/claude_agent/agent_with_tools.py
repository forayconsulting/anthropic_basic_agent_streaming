"""Claude Agent with full MCP tool integration."""

from dataclasses import dataclass
from enum import Enum
from typing import AsyncGenerator, Dict, Any, Optional, List, Tuple
import httpx
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


class ClaudeAgentWithTools:
    """Claude agent with full MCP tool integration."""
    
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
        """
        Stream response from Claude with automatic tool handling.
        
        This method handles the complete tool use cycle:
        1. Send initial request with available MCP tools
        2. If Claude uses tools, execute them via MCP
        3. Send results back to Claude
        4. Get final response
        """
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
        
        # Tool use cycle - may need multiple rounds
        max_rounds = 5  # Prevent infinite loops
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
            
            # Collect the complete response
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
                                # Parse the SSE event
                                if sse_event.event == "message_start":
                                    continue
                                elif sse_event.event == "content_block_delta":
                                    # Stream content to user
                                    for token in self._token_classifier.classify(sse_event):
                                        if token.type == TokenType.THINKING:
                                            event_type = StreamEventType.THINKING
                                        else:
                                            event_type = StreamEventType.RESPONSE
                                        
                                        yield StreamEvent(
                                            type=event_type,
                                            content=token.content,
                                            metadata=token.metadata
                                        )
                                        
                                        # Collect response content
                                        if token.metadata and token.metadata.get("block_type") == "tool_use":
                                            # This is tool use content
                                            pass
                                        else:
                                            response_content.append(token.content)
                                
                                elif sse_event.event == "content_block_stop":
                                    # Check if this was a tool use block
                                    if sse_event.data:
                                        import json
                                        try:
                                            data = json.loads(sse_event.data)
                                            if data.get("type") == "tool_use":
                                                tool_uses.append(AnthropicToolUse(
                                                    id=data.get("id", ""),
                                                    name=data.get("name", ""),
                                                    input=data.get("input", {})
                                                ))
                                                yield StreamEvent(
                                                    type=StreamEventType.TOOL_USE,
                                                    content=f"Using tool: {data.get('name')}",
                                                    metadata={"tool": data}
                                                )
                                        except:
                                            pass
                                
                                elif sse_event.event == "message_delta":
                                    # Check stop reason
                                    if sse_event.data:
                                        import json
                                        try:
                                            data = json.loads(sse_event.data)
                                            delta = data.get("delta", {})
                                            stop_reason = delta.get("stop_reason")
                                        except:
                                            pass
            
            except Exception as e:
                yield StreamEvent(
                    type=StreamEventType.ERROR,
                    content=str(e),
                    metadata={"error_type": type(e).__name__}
                )
                return
            
            # Add assistant message to conversation
            assistant_message = {
                "role": "assistant",
                "content": "".join(response_content) if response_content else []
            }
            
            # If there were tool uses, add them to the message
            if tool_uses:
                assistant_message["content"] = []
                if response_content:
                    assistant_message["content"].append({
                        "type": "text",
                        "text": "".join(response_content)
                    })
                
                for tool_use in tool_uses:
                    assistant_message["content"].append({
                        "type": "tool_use",
                        "id": tool_use.id,
                        "name": tool_use.name,
                        "input": tool_use.input
                    })
            
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
                        content=f"Tool result: {result.content[:100]}...",
                        metadata={
                            "tool_use_id": result.tool_use_id,
                            "is_error": result.is_error
                        }
                    )
                
                # Add tool results to conversation
                tool_result_message = self._bridge.format_tool_response_message(tool_results)
                current_messages.append(tool_result_message)
                
                # Continue the conversation loop
                response_content = []
                tool_uses = []
                
            else:
                # No more tool uses, we're done
                break
        
        yield StreamEvent(type=StreamEventType.DONE, content="")
    
    async def stream_response(
        self,
        system_prompt: str,
        user_prompt: str,
        thinking_budget: Optional[int] = None,
        include_mcp_tools: bool = True,
        max_tokens: int = 4096,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream response from Claude API with optional MCP tool support.
        
        This is a simpler version that doesn't automatically handle tools.
        Use stream_response_with_tools for automatic tool handling.
        """
        # Delegate to tool-enabled version if requested
        if include_mcp_tools and self._mcp_manager.is_connected:
            async for event in self.stream_response_with_tools(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                thinking_budget=thinking_budget,
                max_tokens=max_tokens,
                conversation_history=conversation_history
            ):
                yield event
            return
        
        # Otherwise, simple streaming without tools
        request = self._request_builder.build_request(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            thinking_budget=thinking_budget,
            mcp_context=None,
            max_tokens=max_tokens,
            stream=True,
            conversation_history=conversation_history
        )
        
        headers = self._request_builder.get_headers(streaming=True)
        
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