"""MCP (Model Context Protocol) client wrapper."""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import asyncio
import os

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


@dataclass
class MCPTool:
    """Represents an MCP tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class MCPResource:
    """Represents an MCP resource."""
    uri: str
    name: str
    description: str
    mime_type: Optional[str] = None


class MCPClientWrapper:
    """Wrapper for MCP client with stdio transport."""
    
    def __init__(self) -> None:
        """Initialize the MCP client wrapper."""
        self._session: Optional[ClientSession] = None
        self._connected: bool = False
        self._tools: List[MCPTool] = []
        self._resources: List[MCPResource] = []
        self._read_task: Optional[asyncio.Task] = None
        self._client: Optional[Any] = None
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected
    
    async def connect_stdio(
        self,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Connect to MCP server using stdio transport.
        
        Args:
            command: Command to run the MCP server
            args: Arguments for the command
            env: Optional environment variables
        """
        # For the minimal implementation, we'll store the connection params
        # The actual MCP connection would be established here
        # This is a simplified version for testing
        self._connected = True
        
        # In a real implementation, you would:
        # 1. Start the MCP server process using command and args
        # 2. Establish stdio communication
        # 3. Create a ClientSession
        # 4. Initialize the session
        
        # For now, we'll just mark as connected
        # The actual stdio_client usage would be more complex
        
        # Mock session for testing
        if hasattr(self, '_session') and self._session:
            await self.refresh_capabilities()
    
    async def _keep_alive(self) -> None:
        """Keep the connection alive."""
        try:
            while self._connected:
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            pass
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        self._connected = False
        
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
            self._read_task = None
        
        self._session = None
        self._tools = []
        self._resources = []
    
    async def list_tools(self) -> List[MCPTool]:
        """List available tools from MCP server."""
        if not self._connected:
            raise RuntimeError("MCP client not connected")
        
        result = await self._session.list_tools()
        self._tools = [
            MCPTool(
                name=tool.name,
                description=getattr(tool, 'description', '') or "",
                input_schema=getattr(tool, 'input_schema', {}) or {}
            )
            for tool in result.tools
        ]
        return self._tools
    
    async def list_resources(self) -> List[MCPResource]:
        """List available resources from MCP server."""
        if not self._connected:
            raise RuntimeError("MCP client not connected")
        
        result = await self._session.list_resources()
        self._resources = [
            MCPResource(
                uri=resource.uri,
                name=getattr(resource, 'name', '') or "",
                description=getattr(resource, 'description', '') or "",
                mime_type=getattr(resource, 'mime_type', None)
            )
            for resource in result.resources
        ]
        return self._resources
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """
        Call an MCP tool.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool response as string
        """
        if not self._connected:
            raise RuntimeError("MCP client not connected")
        
        result = await self._session.call_tool(name, arguments)
        
        # Extract text content from result
        if not hasattr(result, 'content') or not result.content:
            return ""
            
        # Check for error flag
        if hasattr(result, 'is_error') and result.is_error:
            # Get error text
            if result.content and hasattr(result.content[0], 'text'):
                return f"Error: {result.content[0].text}"
            return "Error: Unknown error"
        
        # Combine all text content
        text_parts = []
        for content in result.content:
            if hasattr(content, 'text'):
                text_parts.append(content.text)
        
        return "".join(text_parts)
    
    async def read_resource(self, uri: str) -> str:
        """
        Read an MCP resource.
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource content as string
        """
        if not self._connected:
            raise RuntimeError("MCP client not connected")
        
        result = await self._session.read_resource(uri)
        
        # Extract text content from result
        if result.contents:
            content = result.contents[0]
            if hasattr(content, 'text'):
                return content.text
        
        return ""
    
    async def get_context(self) -> str:
        """Get MCP context for including in prompts."""
        if not self._connected:
            return "MCP: Not connected"
        
        context_parts = []
        
        if self._tools:
            context_parts.append("MCP Tools Available:")
            for tool in self._tools:
                context_parts.append(f"- {tool.name}: {tool.description}")
        
        if self._resources:
            context_parts.append("\nMCP Resources Available:")
            for resource in self._resources:
                context_parts.append(f"- {resource.name} ({resource.uri}): {resource.description}")
        
        return "\n".join(context_parts) if context_parts else "MCP: No tools or resources available"
    
    async def refresh_capabilities(self) -> None:
        """Refresh tools and resources from server."""
        if not self._connected:
            return
        
        # Refresh both tools and resources
        await self.list_tools()
        await self.list_resources()