"""Claude Agent - Minimal agent with MCP support and extended thinking."""

__version__ = "0.1.0"

from .agent import ClaudeAgent, StreamEvent, StreamEventType
from .mcp_client import MCPClientWrapper, MCPTool, MCPResource
from .api_request_builder import APIRequestBuilder
from .sse_parser import SSEParser, SSEEvent
from .token_classifier import TokenClassifier, TokenType, ClassifiedToken

# New MCP integration classes
from .mcp_client_fixed import FixedMCPClient, MCPConnectionManager
from .mcp_anthropic_bridge import MCPAnthropicBridge, AnthropicToolUse, AnthropicToolResult, ToolExecutor
from .agent_with_tools import ClaudeAgentWithTools

__all__ = [
    "ClaudeAgent",
    "StreamEvent",
    "StreamEventType",
    "MCPClientWrapper",
    "MCPTool",
    "MCPResource",
    "APIRequestBuilder",
    "SSEParser",
    "SSEEvent", 
    "TokenClassifier",
    "TokenType",
    "ClassifiedToken",
    # New MCP integration
    "FixedMCPClient",
    "MCPConnectionManager",
    "MCPAnthropicBridge",
    "AnthropicToolUse",
    "AnthropicToolResult",
    "ToolExecutor",
    "ClaudeAgentWithTools",
]