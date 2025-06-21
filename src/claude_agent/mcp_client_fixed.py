"""Fixed MCP client implementation that properly maintains stdio connection."""

import asyncio
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable
from contextlib import asynccontextmanager
import logging

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import mcp.types as types

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """Represents an MCP tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    
    def to_anthropic_format(self) -> Dict[str, Any]:
        """Convert to Anthropic tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema
        }


@dataclass
class MCPResource:
    """Represents an MCP resource."""
    uri: str
    name: str
    description: str
    mime_type: Optional[str] = None


class FixedMCPClient:
    """MCP client that properly maintains stdio connection using context managers."""
    
    def __init__(self) -> None:
        """Initialize the MCP client."""
        self._tools: List[MCPTool] = []
        self._resources: List[MCPResource] = []
        self._server_params: Optional[StdioServerParameters] = None
        self._connection_active = False
    
    @asynccontextmanager
    async def connect(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None
    ):
        """
        Connect to MCP server and maintain connection as context manager.
        
        Usage:
            async with client.connect(command, args) as session:
                # Use session here
                tools = await session.list_tools()
        """
        # Prepare server parameters
        server_params = StdioServerParameters(
            command=command,
            args=args or [],
            env=env,
            cwd=cwd
        )
        
        # Connect to server
        async with stdio_client(server_params) as (read_stream, write_stream):
            # Create session
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize session
                await session.initialize()
                
                # Cache tools and resources
                await self._refresh_capabilities(session)
                
                self._connection_active = True
                try:
                    yield session
                finally:
                    self._connection_active = False
    
    async def _refresh_capabilities(self, session: ClientSession) -> None:
        """Refresh tools and resources from server."""
        # Get tools
        try:
            result = await session.list_tools()
            self._tools = [
                MCPTool(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=tool.inputSchema
                )
                for tool in result.tools
            ]
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            self._tools = []
        
        # Get resources
        try:
            result = await session.list_resources()
            self._resources = [
                MCPResource(
                    uri=resource.uri,
                    name=resource.name or "",
                    description=resource.description or "",
                    mime_type=resource.mimeType
                )
                for resource in result.resources
            ]
        except Exception as e:
            logger.error(f"Failed to list resources: {e}")
            self._resources = []
    
    @property
    def tools(self) -> List[MCPTool]:
        """Get cached tools."""
        return self._tools
    
    @property
    def resources(self) -> List[MCPResource]:
        """Get cached resources."""
        return self._resources
    
    @property
    def is_connected(self) -> bool:
        """Check if actively connected."""
        return self._connection_active
    
    def get_anthropic_tools(self) -> List[Dict[str, Any]]:
        """Get tools in Anthropic format."""
        return [tool.to_anthropic_format() for tool in self._tools]
    
    def get_context(self) -> str:
        """Get MCP context for prompts."""
        if not self._connection_active:
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


class MCPConnectionManager:
    """Manages persistent MCP connections for use with Claude."""
    
    def __init__(self) -> None:
        """Initialize the connection manager."""
        self._client = FixedMCPClient()
        self._session: Optional[ClientSession] = None
        self._connection_task: Optional[asyncio.Task] = None
        self._server_params: Optional[Dict[str, Any]] = None
        self._ready_event = asyncio.Event()
    
    async def connect(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None
    ) -> None:
        """Connect to MCP server and maintain connection."""
        if self._connection_task:
            await self.disconnect()
        
        self._server_params = {
            "command": command,
            "args": args,
            "env": env,
            "cwd": cwd
        }
        
        # Start connection in background
        self._connection_task = asyncio.create_task(self._maintain_connection())
        
        # Wait for connection to be ready
        try:
            await asyncio.wait_for(self._ready_event.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            await self.disconnect()
            raise TimeoutError("Failed to connect to MCP server")
    
    async def _maintain_connection(self) -> None:
        """Maintain the MCP connection."""
        try:
            async with self._client.connect(**self._server_params) as session:
                self._session = session
                self._ready_event.set()
                
                # Keep connection alive
                while True:
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            # Normal shutdown
            pass
        except Exception as e:
            logger.error(f"MCP connection error: {e}")
        finally:
            self._session = None
            self._ready_event.clear()
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if self._connection_task:
            self._connection_task.cancel()
            try:
                await self._connection_task
            except asyncio.CancelledError:
                pass
            self._connection_task = None
        
        self._session = None
        self._ready_event.clear()
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool."""
        if not self._session:
            raise RuntimeError("Not connected to MCP server")
        
        result = await self._session.call_tool(name, arguments)
        
        # Extract content based on result type
        if hasattr(result, 'content'):
            # Handle different content types
            content_parts = []
            for content in result.content:
                if hasattr(content, 'text'):
                    content_parts.append(content.text)
                elif hasattr(content, 'type') and content.type == 'text':
                    content_parts.append(content.text)
            return "\n".join(content_parts)
        
        return str(result)
    
    @property
    def tools(self) -> List[MCPTool]:
        """Get available tools."""
        return self._client.tools
    
    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._session is not None
    
    def get_anthropic_tools(self) -> List[Dict[str, Any]]:
        """Get tools in Anthropic format."""
        return self._client.get_anthropic_tools()