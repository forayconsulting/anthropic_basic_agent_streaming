"""Tests for MCP client wrapper."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from types import SimpleNamespace
import asyncio
from typing import Dict, Any

from claude_agent.mcp_client import MCPClientWrapper, MCPTool, MCPResource


class TestMCPClientWrapper:
    """Test cases for MCP client wrapper."""

    @pytest.mark.asyncio
    async def test_initialize_stdio_client(self):
        """Test initializing MCP client with stdio transport."""
        wrapper = MCPClientWrapper()
        
        # For minimal implementation, just verify connection state
        await wrapper.connect_stdio("python", ["-m", "my_mcp_server"])
        
        assert wrapper.is_connected

    @pytest.mark.asyncio
    async def test_initialize_with_env_vars(self):
        """Test initializing MCP client with environment variables."""
        wrapper = MCPClientWrapper()
        
        # For minimal implementation, just verify connection state
        env_vars = {"API_KEY": "test_key", "DEBUG": "true"}
        await wrapper.connect_stdio("node", ["server.js"], env=env_vars)
        
        assert wrapper.is_connected

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing available tools from MCP server."""
        wrapper = MCPClientWrapper()
        
        # Setup mock session
        mock_session = AsyncMock()
        mock_session.list_tools.return_value = SimpleNamespace(
            tools=[
                SimpleNamespace(
                    name="search",
                    description="Search for information",
                    input_schema={"type": "object", "properties": {"query": {"type": "string"}}}
                ),
                SimpleNamespace(
                    name="calculate",
                    description="Perform calculations",
                    input_schema={"type": "object", "properties": {"expression": {"type": "string"}}}
                )
            ]
        )
        wrapper._session = mock_session
        wrapper._connected = True
        
        tools = await wrapper.list_tools()
        
        assert len(tools) == 2
        assert tools[0].name == "search"
        assert tools[0].description == "Search for information"
        assert tools[1].name == "calculate"
        assert tools[1].description == "Perform calculations"

    @pytest.mark.asyncio
    async def test_list_resources(self):
        """Test listing available resources from MCP server."""
        wrapper = MCPClientWrapper()
        
        # Setup mock session
        mock_session = AsyncMock()
        mock_session.list_resources.return_value = SimpleNamespace(
            resources=[
                SimpleNamespace(
                    uri="file:///data/config.json",
                    name="Configuration",
                    description="App configuration file",
                    mime_type="application/json"
                )
            ]
        )
        wrapper._session = mock_session
        wrapper._connected = True
        
        resources = await wrapper.list_resources()
        
        assert len(resources) == 1
        assert resources[0].uri == "file:///data/config.json"
        assert resources[0].name == "Configuration"
        assert resources[0].mime_type == "application/json"

    @pytest.mark.asyncio
    async def test_call_tool(self):
        """Test calling a tool through MCP."""
        wrapper = MCPClientWrapper()
        
        # Setup mock session
        mock_session = AsyncMock()
        mock_session.call_tool.return_value = SimpleNamespace(
            content=[
                SimpleNamespace(
                    type="text",
                    text="Search results for Python"
                )
            ]
        )
        wrapper._session = mock_session
        wrapper._connected = True
        
        result = await wrapper.call_tool("search", {"query": "Python"})
        
        assert result == "Search results for Python"
        mock_session.call_tool.assert_called_once_with("search", {"query": "Python"})

    @pytest.mark.asyncio
    async def test_read_resource(self):
        """Test reading a resource through MCP."""
        wrapper = MCPClientWrapper()
        
        # Setup mock session
        mock_session = AsyncMock()
        mock_session.read_resource.return_value = SimpleNamespace(
            contents=[
                SimpleNamespace(
                    uri="file:///data/config.json",
                    text='{"debug": true}'
                )
            ]
        )
        wrapper._session = mock_session
        wrapper._connected = True
        
        content = await wrapper.read_resource("file:///data/config.json")
        
        assert content == '{"debug": true}'
        mock_session.read_resource.assert_called_once_with("file:///data/config.json")

    @pytest.mark.asyncio
    async def test_get_context_for_prompt(self):
        """Test getting MCP context for including in prompts."""
        wrapper = MCPClientWrapper()
        
        # Setup mock data
        wrapper._connected = True
        wrapper._tools = [
            MCPTool(
                name="search",
                description="Search for information",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}}
            )
        ]
        wrapper._resources = [
            MCPResource(
                uri="file:///config.json",
                name="Config",
                description="Configuration file",
                mime_type="application/json"
            )
        ]
        
        context = await wrapper.get_context()
        
        assert "MCP Tools Available:" in context
        assert "search: Search for information" in context
        assert "MCP Resources Available:" in context
        assert "Config (file:///config.json): Configuration file" in context

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnecting from MCP server."""
        wrapper = MCPClientWrapper()
        
        # Setup mock session
        mock_session = AsyncMock()
        wrapper._session = mock_session
        wrapper._connected = True
        wrapper._read_task = asyncio.create_task(asyncio.sleep(0))
        
        await wrapper.disconnect()
        
        assert not wrapper.is_connected
        assert wrapper._session is None
        assert wrapper._read_task is None

    @pytest.mark.asyncio
    async def test_not_connected_error(self):
        """Test error when calling methods without connection."""
        wrapper = MCPClientWrapper()
        
        with pytest.raises(RuntimeError, match="MCP client not connected"):
            await wrapper.list_tools()
        
        with pytest.raises(RuntimeError, match="MCP client not connected"):
            await wrapper.call_tool("search", {"query": "test"})

    @pytest.mark.asyncio
    async def test_handle_tool_error(self):
        """Test handling errors from tool calls."""
        wrapper = MCPClientWrapper()
        
        # Setup mock session
        mock_session = AsyncMock()
        mock_session.call_tool.return_value = SimpleNamespace(
            content=[
                SimpleNamespace(
                    type="text",
                    text="Error: Tool execution failed"
                )
            ],
            is_error=True
        )
        wrapper._session = mock_session
        wrapper._connected = True
        
        result = await wrapper.call_tool("broken_tool", {})
        
        assert "Error: Tool execution failed" in result

    @pytest.mark.asyncio
    async def test_empty_tool_response(self):
        """Test handling empty tool response."""
        wrapper = MCPClientWrapper()
        
        # Setup mock session
        mock_session = AsyncMock()
        mock_session.call_tool.return_value = SimpleNamespace(content=[])
        wrapper._session = mock_session
        wrapper._connected = True
        
        result = await wrapper.call_tool("silent_tool", {})
        
        assert result == ""

    @pytest.mark.asyncio
    async def test_refresh_capabilities(self):
        """Test refreshing tools and resources from server."""
        wrapper = MCPClientWrapper()
        
        # Setup mock session
        mock_session = AsyncMock()
        mock_session.list_tools.return_value = SimpleNamespace(
            tools=[
                SimpleNamespace(
                    name="new_tool",
                    description="A new tool",
                    input_schema={}
                )
            ]
        )
        mock_session.list_resources.return_value = SimpleNamespace(resources=[])
        
        wrapper._session = mock_session
        wrapper._connected = True
        
        # Initially empty
        assert len(wrapper._tools) == 0
        
        await wrapper.refresh_capabilities()
        
        assert len(wrapper._tools) == 1
        assert wrapper._tools[0].name == "new_tool"