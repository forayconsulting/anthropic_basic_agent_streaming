"""Improved MCP client with better error handling and debugging."""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import asyncio
import os
import json
import sys

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError as e:
    print(f"Error importing MCP: {e}")
    print("Please install: pip install mcp")
    sys.exit(1)


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


class MCPClientV2:
    """Improved MCP client with better debugging."""
    
    def __init__(self, debug: bool = True) -> None:
        """Initialize the MCP client."""
        self._session: Optional[ClientSession] = None
        self._tools: List[MCPTool] = []
        self._resources: List[MCPResource] = []
        self._debug = debug
        self._process = None
        
    def _log(self, message: str) -> None:
        """Log debug message."""
        if self._debug:
            print(f"[MCP] {message}")
    
    async def connect(
        self,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None
    ) -> None:
        """Connect to MCP server with improved error handling."""
        self._log(f"Connecting to MCP server: {command} {' '.join(args)}")
        
        # Prepare environment
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
            self._log(f"Environment variables: {list(env.keys())}")
        
        # Create server parameters
        params = StdioServerParameters(
            command=command,
            args=args,
            env=full_env
        )
        
        try:
            # Use stdio_client context manager
            self._log("Creating stdio connection...")
            
            # Start the server process
            read_stream, write_stream = await stdio_client.__aenter__(params)
            
            self._log("Stdio streams created")
            
            # Create session
            self._session = ClientSession(read_stream, write_stream)
            self._log("Session created")
            
            # Initialize with timeout
            self._log("Initializing session...")
            await asyncio.wait_for(self._session.initialize(), timeout=10.0)
            self._log("Session initialized successfully")
            
            # List capabilities immediately
            await self._refresh_capabilities()
            
        except asyncio.TimeoutError:
            self._log("Timeout during initialization")
            raise RuntimeError("MCP server initialization timed out")
        except Exception as e:
            self._log(f"Connection error: {type(e).__name__}: {e}")
            raise
    
    async def _refresh_capabilities(self) -> None:
        """Refresh tools and resources."""
        try:
            # List tools
            self._log("Listing tools...")
            tools_result = await self._session.list_tools()
            
            if hasattr(tools_result, 'tools'):
                self._tools = [
                    MCPTool(
                        name=tool.name,
                        description=getattr(tool, 'description', ''),
                        input_schema=getattr(tool, 'inputSchema', {})
                    )
                    for tool in tools_result.tools
                ]
                self._log(f"Found {len(self._tools)} tools")
            else:
                self._log("No tools attribute in response")
                
            # List resources
            self._log("Listing resources...")
            resources_result = await self._session.list_resources()
            
            if hasattr(resources_result, 'resources'):
                self._resources = [
                    MCPResource(
                        uri=resource.uri,
                        name=getattr(resource, 'name', ''),
                        description=getattr(resource, 'description', ''),
                        mime_type=getattr(resource, 'mimeType', None)
                    )
                    for resource in resources_result.resources
                ]
                self._log(f"Found {len(self._resources)} resources")
            else:
                self._log("No resources attribute in response")
                
        except Exception as e:
            self._log(f"Error refreshing capabilities: {type(e).__name__}: {e}")
            # Don't raise - server might not support all capabilities
    
    def get_tools(self) -> List[MCPTool]:
        """Get available tools."""
        return self._tools
    
    def get_resources(self) -> List[MCPResource]:
        """Get available resources."""
        return self._resources
    
    def get_context(self) -> str:
        """Get context string for prompts."""
        parts = []
        
        if self._tools:
            parts.append("MCP Tools Available:")
            for tool in self._tools:
                parts.append(f"- {tool.name}: {tool.description}")
        
        if self._resources:
            parts.append("\nMCP Resources Available:")
            for resource in self._resources:
                parts.append(f"- {resource.name} ({resource.uri})")
        
        return "\n".join(parts) if parts else "MCP: No tools or resources available"
    
    async def disconnect(self) -> None:
        """Disconnect from server."""
        if self._session:
            try:
                await self._session.close()
            except:
                pass
            self._session = None


async def test_mcp_v2():
    """Test the improved MCP client."""
    print("Testing MCP Client V2\n")
    
    client = MCPClientV2(debug=True)
    
    # Test with GitHub server
    token = "your_github_token_here"
    
    try:
        await client.connect(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": token}
        )
        
        print(f"\nTools: {len(client.get_tools())}")
        for tool in client.get_tools():
            print(f"  - {tool.name}: {tool.description}")
        
        print(f"\nContext:\n{client.get_context()}")
        
        await client.disconnect()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_mcp_v2())