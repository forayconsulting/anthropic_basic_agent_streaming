"""MCP Session Manager that handles persistent connections properly."""

import asyncio
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable
import logging
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


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


class MCPSessionManager:
    """Manages MCP sessions with proper lifecycle handling."""
    
    def __init__(self) -> None:
        """Initialize the session manager."""
        self._params: Optional[StdioServerParameters] = None
        self._tools: List[MCPTool] = []
        self._resources: List[MCPResource] = []
        self._is_connected = False
        self._connection_info: Dict[str, Any] = {}
        
    async def initialize_connection(
        self,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Initialize connection parameters and test the connection.
        This doesn't maintain a persistent connection but validates it works.
        """
        # Merge environment
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
            logger.info(f"MCP: Setting environment variables: {list(env.keys())}")
        
        # Store parameters
        self._params = StdioServerParameters(
            command=command,
            args=args or [],
            env=full_env
        )
        
        # Store connection info
        self._connection_info = {
            "command": command,
            "args": args,
            "env_keys": list(env.keys()) if env else []
        }
        
        # Test connection and get capabilities
        logger.info(f"MCP: Testing connection to {command} {' '.join(args)}")
        
        try:
            async with stdio_client(self._params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    # Initialize session
                    await session.initialize()
                    
                    # Get capabilities
                    await self._fetch_capabilities(session)
                    
            self._is_connected = True
            logger.info(f"MCP: Connection successful - {len(self._tools)} tools, {len(self._resources)} resources")
            
        except Exception as e:
            logger.error(f"MCP: Connection failed - {type(e).__name__}: {e}")
            self._is_connected = False
            raise
    
    async def _fetch_capabilities(self, session: ClientSession) -> None:
        """Fetch tools and resources from the session."""
        # Get tools
        try:
            logger.info("MCP: Fetching tools...")
            result = await session.list_tools()
            
            self._tools = []
            if hasattr(result, 'tools') and result.tools:
                for tool in result.tools:
                    self._tools.append(MCPTool(
                        name=tool.name,
                        description=getattr(tool, 'description', ''),
                        input_schema=getattr(tool, 'inputSchema', {})
                    ))
                logger.info(f"MCP: Found {len(self._tools)} tools")
                
                # Log first few tools
                for tool in self._tools[:3]:
                    logger.info(f"  - {tool.name}: {tool.description[:50]}...")
            else:
                logger.warning("MCP: No tools found in response")
                
        except Exception as e:
            logger.error(f"MCP: Error fetching tools - {e}")
        
        # Get resources  
        try:
            logger.info("MCP: Fetching resources...")
            result = await session.list_resources()
            
            self._resources = []
            if hasattr(result, 'resources') and result.resources:
                for resource in result.resources:
                    self._resources.append(MCPResource(
                        uri=resource.uri,
                        name=getattr(resource, 'name', ''),
                        description=getattr(resource, 'description', ''),
                        mime_type=getattr(resource, 'mimeType', None)
                    ))
                logger.info(f"MCP: Found {len(self._resources)} resources")
            else:
                logger.warning("MCP: No resources found in response")
                
        except Exception as e:
            logger.error(f"MCP: Error fetching resources - {e}")
    
    async def execute_with_session(self, func: Callable) -> Any:
        """
        Execute a function with an active MCP session.
        This creates a new connection for each execution.
        """
        if not self._params:
            raise RuntimeError("MCP not initialized - call initialize_connection first")
        
        async with stdio_client(self._params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                return await func(session)
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Call a tool using a fresh session."""
        async def _call(session):
            result = await session.call_tool(name, arguments)
            
            # Extract text content
            if hasattr(result, 'isError') and result.isError:
                if hasattr(result, 'content') and result.content:
                    return f"Error: {result.content[0].text if hasattr(result.content[0], 'text') else 'Unknown error'}"
                return "Error: Unknown error"
            
            # Combine text content
            text_parts = []
            if hasattr(result, 'content'):
                for content in result.content:
                    if hasattr(content, 'text'):
                        text_parts.append(content.text)
            
            return "".join(text_parts)
        
        return await self.execute_with_session(_call)
    
    def get_tools(self) -> List[MCPTool]:
        """Get cached tools."""
        return self._tools
    
    def get_resources(self) -> List[MCPResource]:
        """Get cached resources."""
        return self._resources
    
    def get_context(self) -> str:
        """Get context string for prompts."""
        if not self._is_connected:
            return "MCP: Not connected"
        
        parts = []
        
        if self._tools:
            parts.append("MCP Tools Available:")
            for tool in self._tools:
                parts.append(f"- {tool.name}: {tool.description}")
        
        if self._resources:
            parts.append("\nMCP Resources Available:")
            for resource in self._resources:
                parts.append(f"- {resource.name} ({resource.uri}): {resource.description}")
        
        return "\n".join(parts) if parts else "MCP: No tools or resources available"
    
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._is_connected
    
    def disconnect(self) -> None:
        """Clear connection state."""
        self._is_connected = False
        self._params = None
        self._tools = []
        self._resources = []
        self._connection_info = {}