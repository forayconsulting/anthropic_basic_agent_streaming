"""Real MCP (Model Context Protocol) client implementation with stdio transport."""

import asyncio
import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import Tool, Resource


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


class RealMCPClient:
    """Real MCP client implementation with stdio transport."""
    
    def __init__(self) -> None:
        """Initialize the MCP client."""
        self._session: Optional[ClientSession] = None
        self._client_task: Optional[asyncio.Task] = None
        self._tools: List[MCPTool] = []
        self._resources: List[MCPResource] = []
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._session is not None
    
    async def connect_stdio(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None
    ) -> None:
        """
        Connect to MCP server using stdio transport.
        
        Args:
            command: Command to run the MCP server
            args: Arguments for the command
            env: Optional environment variables
            cwd: Optional working directory
        """
        if self._session:
            await self.disconnect()
        
        # Prepare server parameters
        server_params = StdioServerParameters(
            command=command,
            args=args or [],
            env=env,
            cwd=cwd
        )
        
        # Use stdio_client as a context manager
        async with stdio_client(server_params) as (read_stream, write_stream):
            # Create session with the streams
            self._session = ClientSession(read_stream, write_stream)
            
            # Initialize the session
            await self._session.initialize()
            
            # Store the streams for later use
            self._read_stream = read_stream
            self._write_stream = write_stream
            
            # Start the read loop
            self._client_task = asyncio.create_task(self._run_client(read_stream, write_stream))
            
            # Refresh capabilities
            await self.refresh_capabilities()
            
            # Exit the context manager but keep the connection alive
            # The streams remain open until we explicitly close them
    
    async def _run_client(self, read_stream: Any, write_stream: Any) -> None:
        """Run the client read loop."""
        try:
            async for message in read_stream:
                # Process messages if needed
                pass
        except Exception as e:
            print(f"Client error: {e}")
        finally:
            write_stream.close()
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if self._client_task:
            self._client_task.cancel()
            try:
                await self._client_task
            except asyncio.CancelledError:
                pass
            self._client_task = None
        
        if self._session:
            await self._session.close()
            self._session = None
        
        self._tools = []
        self._resources = []
    
    async def list_tools(self) -> List[MCPTool]:
        """List available tools from MCP server."""
        if not self._session:
            raise RuntimeError("MCP client not connected")
        
        result = await self._session.list_tools()
        self._tools = [
            MCPTool(
                name=tool.name,
                description=tool.description or "",
                input_schema=tool.inputSchema
            )
            for tool in result.tools
        ]
        return self._tools
    
    async def list_resources(self) -> List[MCPResource]:
        """List available resources from MCP server."""
        if not self._session:
            raise RuntimeError("MCP client not connected")
        
        result = await self._session.list_resources()
        self._resources = [
            MCPResource(
                uri=resource.uri,
                name=resource.name or "",
                description=resource.description or "",
                mime_type=resource.mimeType
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
        if not self._session:
            raise RuntimeError("MCP client not connected")
        
        result = await self._session.call_tool(name, arguments)
        
        # Extract text content from result
        if result.isError:
            # Handle error response
            if result.content and len(result.content) > 0:
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
        if not self._session:
            raise RuntimeError("MCP client not connected")
        
        result = await self._session.read_resource(uri)
        
        # Extract text content from result
        if result.contents and len(result.contents) > 0:
            content = result.contents[0]
            if hasattr(content, 'text'):
                return content.text
        
        return ""
    
    async def get_context(self) -> str:
        """Get MCP context for including in prompts."""
        if not self._session:
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
        if not self._session:
            return
        
        # Refresh both tools and resources
        await self.list_tools()
        await self.list_resources()