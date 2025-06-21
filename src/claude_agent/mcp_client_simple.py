"""Simple MCP client implementation."""

import asyncio
import json
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


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


class SimpleMCPClient:
    """Simple MCP client for testing."""
    
    def __init__(self) -> None:
        """Initialize the client."""
        self._tools: List[MCPTool] = []
        self._resources: List[MCPResource] = []
    
    @asynccontextmanager
    async def create_session(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None
    ):
        """
        Create an MCP session context manager.
        
        Args:
            command: Command to run the MCP server
            args: Arguments for the command
            env: Optional environment variables
            cwd: Optional working directory
            
        Yields:
            ClientSession instance
        """
        # Prepare server parameters
        server_params = StdioServerParameters(
            command=command,
            args=args or [],
            env=env,
            cwd=cwd
        )
        
        # Use stdio_client as a context manager
        async with stdio_client(server_params) as (read_stream, write_stream):
            # Create session
            session = ClientSession(read_stream, write_stream)
            
            try:
                # Initialize session
                await session.initialize()
                
                # Store session data
                result = await session.list_tools()
                self._tools = [
                    MCPTool(
                        name=tool.name,
                        description=tool.description or "",
                        input_schema=tool.inputSchema
                    )
                    for tool in result.tools
                ]
                
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
                
                yield session
                
            finally:
                # Clean up
                await session.close()
    
    @property
    def tools(self) -> List[MCPTool]:
        """Get cached tools."""
        return self._tools
    
    @property
    def resources(self) -> List[MCPResource]:
        """Get cached resources."""
        return self._resources
    
    def get_context(self) -> str:
        """Get MCP context for prompts."""
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