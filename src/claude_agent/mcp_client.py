"""MCP (Model Context Protocol) client wrapper."""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import asyncio
import os

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


class MCPClientWrapper:
    """Wrapper for MCP client with stdio transport."""
    
    def __init__(self) -> None:
        """Initialize the MCP client wrapper."""
        self._session: Optional[ClientSession] = None
        self._stdio_task: Optional[asyncio.Task] = None
        self._tools: List[MCPTool] = []
        self._resources: List[MCPResource] = []
        self._server_params: Optional[StdioServerParameters] = None
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._session is not None
    
    async def connect_stdio(
        self,
        command: str,
        args: List[str],
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
        
        # Merge environment variables with current environment
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
            print(f"MCP Debug - Environment variables being passed: {list(env.keys())}")
        
        # Store server parameters
        self._server_params = StdioServerParameters(
            command=command,
            args=args or [],
            env=full_env,  # Use merged environment
            cwd=cwd
        )
        
        print(f"MCP Debug - Starting server: {command} {' '.join(args)}")
        
        # Start the stdio connection in a background task
        self._stdio_task = asyncio.create_task(self._run_stdio_connection())
        
        # Wait for connection to be established with timeout
        retries = 0
        error_message = None
        while retries < 100:  # 10 seconds timeout
            await asyncio.sleep(0.1)
            retries += 1
            
            # Check if task failed
            if self._stdio_task.done():
                try:
                    # This will raise if there was an exception
                    await self._stdio_task
                except Exception as e:
                    error_message = str(e)
                    print(f"MCP Debug - Task failed: {error_message}")
                    break
            
            # Check if session is established
            if self._session:
                print("MCP Debug - Session established successfully")
                break
        
        if not self._session:
            if error_message:
                raise RuntimeError(f"MCP connection failed: {error_message}")
            else:
                raise TimeoutError("Failed to establish MCP connection after 10 seconds")
    
    async def _run_stdio_connection(self) -> None:
        """Run the stdio connection in the background."""
        try:
            print("MCP Debug - Starting stdio client...")
            async with stdio_client(self._server_params) as (read_stream, write_stream):
                print("MCP Debug - Stdio streams created")
                
                # Create and initialize session
                self._session = ClientSession(read_stream, write_stream)
                print("MCP Debug - Initializing session...")
                await self._session.initialize()
                print("MCP Debug - Session initialized")
                
                # Refresh capabilities
                print("MCP Debug - Refreshing capabilities...")
                await self.refresh_capabilities()
                print(f"MCP Debug - Found {len(self._tools)} tools and {len(self._resources)} resources")
                
                # Keep the connection alive
                try:
                    # Read messages until cancelled
                    while True:
                        await asyncio.sleep(1)
                except asyncio.CancelledError:
                    # Clean shutdown
                    pass
                finally:
                    await self._session.close()
                    self._session = None
                    
        except Exception as e:
            print(f"MCP connection error: {e}")
            import traceback
            traceback.print_exc()
            self._session = None
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if self._stdio_task:
            self._stdio_task.cancel()
            try:
                await self._stdio_task
            except asyncio.CancelledError:
                pass
            self._stdio_task = None
        
        self._session = None
        self._tools = []
        self._resources = []
    
    async def list_tools(self) -> List[MCPTool]:
        """List available tools from MCP server."""
        if not self._session:
            raise RuntimeError("MCP client not connected")
        
        print("MCP Debug - Listing tools...")
        result = await self._session.list_tools()
        print(f"MCP Debug - Server returned {len(result.tools) if result.tools else 0} tools")
        
        self._tools = [
            MCPTool(
                name=tool.name,
                description=tool.description or "",
                input_schema=tool.inputSchema
            )
            for tool in result.tools
        ]
        
        if self._tools:
            print("MCP Debug - Tools found:")
            for tool in self._tools[:3]:  # Show first 3 tools
                print(f"  - {tool.name}: {tool.description[:50]}...")
        
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
            print("MCP Debug - No session available for refresh_capabilities")
            return
        
        try:
            # Refresh both tools and resources
            print("MCP Debug - Refreshing tools...")
            await self.list_tools()
            print("MCP Debug - Refreshing resources...")
            await self.list_resources()
        except Exception as e:
            print(f"MCP Debug - Error refreshing capabilities: {e}")
            import traceback
            traceback.print_exc()