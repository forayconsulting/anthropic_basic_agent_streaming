#!/usr/bin/env python3
"""Example of using Claude Agent with MCP integration."""

import asyncio
import os
from claude_agent.agent_with_mcp import ClaudeAgentWithMCP, StreamEventType


async def demonstrate_mcp_usage():
    """Demonstrate MCP usage with Claude Agent."""
    
    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set")
        return
    
    # Create agent
    agent = ClaudeAgentWithMCP(api_key=api_key)
    
    try:
        # Example 1: Connect to filesystem MCP server
        print("Example 1: Filesystem MCP Server")
        print("=" * 60)
        
        print("Connecting to filesystem MCP server...")
        await agent.connect_mcp(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        )
        print("✓ Connected!")
        
        # List available tools
        tools = await agent.mcp_client.list_tools()
        print(f"\nAvailable tools: {[tool.name for tool in tools]}")
        
        # Stream a response with MCP context
        print("\n\nAsking Claude about available MCP tools...")
        print("-" * 40)
        
        async for event in agent.stream_response(
            system_prompt="You are a helpful assistant that can use MCP tools.",
            user_prompt="What MCP tools do you have available? Please list them briefly.",
            include_mcp_context=True
        ):
            if event.type == StreamEventType.RESPONSE:
                print(event.content, end="", flush=True)
            elif event.type == StreamEventType.ERROR:
                print(f"\nError: {event.content}")
        
        print("\n")
        
        # Example 2: Call an MCP tool
        if any(tool.name == "read_file" for tool in tools):
            print("\n\nExample 2: Using MCP Tool")
            print("=" * 60)
            
            # Create a test file
            test_file = "/tmp/test_mcp.txt"
            with open(test_file, "w") as f:
                f.write("Hello from MCP test!\nThis is a test file.")
            
            print(f"Created test file: {test_file}")
            print("\nCalling read_file tool and asking Claude to summarize...")
            print("-" * 40)
            
            async for event in agent.call_mcp_tool(
                tool_name="read_file",
                arguments={"path": test_file},
                result_prompt="Please summarize what you found in this file."
            ):
                if event.type == StreamEventType.RESPONSE:
                    print(event.content, end="", flush=True)
                elif event.type == StreamEventType.ERROR:
                    print(f"\nError: {event.content}")
            
            print("\n")
        
        # Example 3: Extended thinking with MCP context
        print("\n\nExample 3: Extended Thinking with MCP")
        print("=" * 60)
        
        thinking_tokens = []
        response_tokens = []
        
        print("Asking a question that requires thinking...")
        print("-" * 40)
        
        async for event in agent.stream_response(
            system_prompt="You are a helpful assistant with MCP tools.",
            user_prompt="Think step by step about how you would use the available MCP tools to organize files in a directory.",
            thinking_budget=5000,
            include_mcp_context=True
        ):
            if event.type == StreamEventType.THINKING:
                thinking_tokens.append(event.content)
            elif event.type == StreamEventType.RESPONSE:
                response_tokens.append(event.content)
                print(event.content, end="", flush=True)
            elif event.type == StreamEventType.ERROR:
                print(f"\nError: {event.content}")
        
        print(f"\n\nThinking tokens: {len(thinking_tokens)}")
        print(f"Response tokens: {len(response_tokens)}")
        
    except Exception as e:
        print(f"\nUnexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Disconnect
        print("\n\nDisconnecting from MCP server...")
        await agent.disconnect_mcp()
        print("✓ Disconnected")


async def test_with_local_server():
    """Test with a specific local MCP server."""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set")
        return
    
    agent = ClaudeAgentWithMCP(api_key=api_key)
    
    # Replace with your actual MCP server configuration
    # This example assumes you have a local MCP server running
    server_configs = [
        {
            "name": "filesystem",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        },
        # Add your other MCP servers here
        # {
        #     "name": "your-server",
        #     "command": "your-command",
        #     "args": ["your", "args"]
        # }
    ]
    
    for config in server_configs:
        print(f"\n\nTesting with {config['name']} server")
        print("=" * 60)
        
        try:
            await agent.connect_mcp(
                command=config["command"],
                args=config["args"]
            )
            
            # Get available tools
            tools = await agent.mcp_client.list_tools()
            resources = await agent.mcp_client.list_resources()
            
            print(f"Tools: {len(tools)}")
            print(f"Resources: {len(resources)}")
            
            # Ask Claude about the server
            async for event in agent.stream_response(
                system_prompt="You are a helpful assistant.",
                user_prompt=f"I just connected to the {config['name']} MCP server. What tools are available?",
                include_mcp_context=True
            ):
                if event.type == StreamEventType.RESPONSE:
                    print(event.content, end="", flush=True)
            
            print("\n")
            
        except Exception as e:
            print(f"Error with {config['name']}: {e}")
        
        finally:
            await agent.disconnect_mcp()


if __name__ == "__main__":
    print("Claude Agent MCP Integration Demo")
    print("=" * 60)
    print("\n1. Basic MCP usage demonstration")
    print("2. Test with specific local servers")
    print("\nChoose an option (1 or 2): ", end="", flush=True)
    
    choice = input().strip()
    
    if choice == "1":
        asyncio.run(demonstrate_mcp_usage())
    elif choice == "2":
        asyncio.run(test_with_local_server())
    else:
        print("Invalid choice")