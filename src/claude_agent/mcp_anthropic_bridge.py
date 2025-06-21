"""Bridge between MCP tools and Anthropic's tool use API."""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class AnthropicToolUse:
    """Represents a tool use request from Claude."""
    id: str
    name: str
    input: Dict[str, Any]


@dataclass
class AnthropicToolResult:
    """Represents a tool result to send back to Claude."""
    tool_use_id: str
    content: str
    is_error: bool = False
    
    def to_content_block(self) -> Dict[str, Any]:
        """Convert to Anthropic content block format."""
        return {
            "type": "tool_result",
            "tool_use_id": self.tool_use_id,
            "content": self.content,
            "is_error": self.is_error
        }


class MCPAnthropicBridge:
    """Bridges MCP tools with Anthropic's tool use API."""
    
    @staticmethod
    def convert_mcp_to_anthropic_tool(mcp_tool: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert MCP tool format to Anthropic tool format.
        
        MCP format:
        {
            "name": "tool_name",
            "description": "description",
            "inputSchema": {...}
        }
        
        Anthropic format:
        {
            "name": "tool_name",
            "description": "description",
            "input_schema": {...}
        }
        """
        return {
            "name": mcp_tool.get("name", ""),
            "description": mcp_tool.get("description", ""),
            "input_schema": mcp_tool.get("inputSchema", mcp_tool.get("input_schema", {}))
        }
    
    @staticmethod
    def extract_tool_uses(message: Dict[str, Any]) -> List[AnthropicToolUse]:
        """Extract tool use requests from Claude's response."""
        tool_uses = []
        
        # Check if this is a tool use response
        if message.get("stop_reason") == "tool_use":
            # Extract tool uses from content blocks
            content = message.get("content", [])
            for block in content:
                if block.get("type") == "tool_use":
                    tool_uses.append(AnthropicToolUse(
                        id=block.get("id", ""),
                        name=block.get("name", ""),
                        input=block.get("input", {})
                    ))
        
        return tool_uses
    
    @staticmethod
    def format_tool_response_message(tool_results: List[AnthropicToolResult]) -> Dict[str, Any]:
        """Format tool results as a user message for Claude."""
        return {
            "role": "user",
            "content": [result.to_content_block() for result in tool_results]
        }
    
    @staticmethod
    def parse_mcp_tool_result(result: Any) -> str:
        """Parse MCP tool result into a string."""
        if isinstance(result, str):
            return result
        
        # Handle MCP result objects
        if hasattr(result, 'content'):
            content_parts = []
            for content in result.content:
                if hasattr(content, 'text'):
                    content_parts.append(content.text)
                elif isinstance(content, dict) and content.get('type') == 'text':
                    content_parts.append(content.get('text', ''))
            return "\n".join(content_parts)
        
        # Handle structured data
        try:
            return json.dumps(result, indent=2)
        except:
            return str(result)
    
    @staticmethod
    def validate_tool_arguments(tool_schema: Dict[str, Any], arguments: Dict[str, Any]) -> Optional[str]:
        """
        Validate tool arguments against schema.
        Returns error message if invalid, None if valid.
        """
        if not tool_schema:
            return None
        
        # Check required fields
        required = tool_schema.get("required", [])
        for field in required:
            if field not in arguments:
                return f"Missing required field: {field}"
        
        # Check property types (basic validation)
        properties = tool_schema.get("properties", {})
        for key, value in arguments.items():
            if key in properties:
                expected_type = properties[key].get("type")
                if expected_type:
                    if expected_type == "string" and not isinstance(value, str):
                        return f"Field {key} must be a string"
                    elif expected_type == "number" and not isinstance(value, (int, float)):
                        return f"Field {key} must be a number"
                    elif expected_type == "boolean" and not isinstance(value, bool):
                        return f"Field {key} must be a boolean"
                    elif expected_type == "object" and not isinstance(value, dict):
                        return f"Field {key} must be an object"
                    elif expected_type == "array" and not isinstance(value, list):
                        return f"Field {key} must be an array"
        
        return None


class ToolExecutor:
    """Executes tools and handles results."""
    
    def __init__(self, mcp_session):
        """Initialize with MCP session."""
        self.mcp_session = mcp_session
    
    async def execute_tool(self, tool_use: AnthropicToolUse, tool_schema: Dict[str, Any]) -> AnthropicToolResult:
        """Execute a tool and return the result."""
        try:
            # Validate arguments
            error = MCPAnthropicBridge.validate_tool_arguments(tool_schema, tool_use.input)
            if error:
                return AnthropicToolResult(
                    tool_use_id=tool_use.id,
                    content=f"Invalid arguments: {error}",
                    is_error=True
                )
            
            # Execute via MCP
            logger.info(f"Executing tool {tool_use.name} with args: {tool_use.input}")
            result = await self.mcp_session.call_tool(tool_use.name, tool_use.input)
            
            # Parse result
            content = MCPAnthropicBridge.parse_mcp_tool_result(result)
            
            return AnthropicToolResult(
                tool_use_id=tool_use.id,
                content=content,
                is_error=False
            )
            
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return AnthropicToolResult(
                tool_use_id=tool_use.id,
                content=f"Tool execution failed: {str(e)}",
                is_error=True
            )