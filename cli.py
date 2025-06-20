#!/usr/bin/env python3
"""CLI interface for testing Claude Agent."""

import asyncio
import os
import sys
import argparse
from typing import Optional, List, Dict
import json

from claude_agent.agent import ClaudeAgent, StreamEventType


class ClaudeCLI:
    """CLI interface for Claude Agent."""
    
    def __init__(self, api_key: str, model: str = "claude-opus-4-20250514"):
        """Initialize CLI with agent."""
        self.agent = ClaudeAgent(api_key=api_key, model=model)
        self.conversation_history: List[Dict[str, str]] = []
        self.system_prompt = "You are a helpful assistant."
        self.thinking_budget: Optional[int] = None
        self.max_tokens = 4096
        self.show_thinking = True
    
    async def run(self):
        """Run the interactive CLI."""
        print("Claude Agent CLI")
        print("=" * 50)
        print(f"Model: {self.agent._model}")
        print(f"System prompt: {self.system_prompt}")
        print("\nCommands:")
        print("  /system <prompt>  - Set system prompt")
        print("  /thinking <budget> - Enable extended thinking (min 1024)")
        print("  /thinking off     - Disable extended thinking")
        print("  /tokens <max>     - Set max tokens (default 4096)")
        print("  /history          - Show conversation history")
        print("  /clear            - Clear conversation history")
        print("  /mcp <cmd> <args> - Connect to MCP server")
        print("  /mcp disconnect   - Disconnect from MCP")
        print("  /mcp status       - Show MCP connection status")
        print("  /hide-thinking    - Hide thinking output")
        print("  /show-thinking    - Show thinking output")
        print("  /help             - Show this help")
        print("  /exit             - Exit CLI")
        print("\nType your message or a command...")
        print("=" * 50)
        
        while True:
            try:
                # Get user input
                user_input = input("\n> ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith("/"):
                    await self.handle_command(user_input)
                    continue
                
                # Regular message
                await self.send_message(user_input)
                
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"\nError: {e}")
        
        # Cleanup
        if self.agent._mcp_connected:
            await self.agent.disconnect_mcp()
    
    async def handle_command(self, command: str):
        """Handle CLI commands."""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd == "/exit":
            print("Goodbye!")
            sys.exit(0)
        
        elif cmd == "/help":
            print("\nCommands:")
            print("  /system <prompt>  - Set system prompt")
            print("  /thinking <budget> - Enable extended thinking (min 1024)")
            print("  /thinking off     - Disable extended thinking")
            print("  /tokens <max>     - Set max tokens (default 4096)")
            print("  /history          - Show conversation history")
            print("  /clear            - Clear conversation history")
            print("  /mcp <cmd> <args> - Connect to MCP server")
            print("  /mcp disconnect   - Disconnect from MCP")
            print("  /mcp status       - Show MCP connection status")
            print("  /hide-thinking    - Hide thinking output")
            print("  /show-thinking    - Show thinking output")
            print("  /help             - Show this help")
            print("  /exit             - Exit CLI")
        
        elif cmd == "/system":
            if args:
                self.system_prompt = args
                print(f"System prompt set to: {self.system_prompt}")
            else:
                print(f"Current system prompt: {self.system_prompt}")
        
        elif cmd == "/thinking":
            if args.lower() == "off":
                self.thinking_budget = None
                print("Extended thinking disabled")
            else:
                try:
                    budget = int(args)
                    if budget < 1024:
                        print("Thinking budget must be at least 1024")
                    elif budget > 128000:
                        print("Thinking budget cannot exceed 128000")
                    else:
                        self.thinking_budget = budget
                        # Ensure max_tokens is greater than thinking budget
                        if self.max_tokens <= budget:
                            self.max_tokens = budget + 1000
                            print(f"Max tokens increased to {self.max_tokens}")
                        print(f"Extended thinking enabled with budget: {budget}")
                except ValueError:
                    print("Invalid thinking budget. Use a number or 'off'")
        
        elif cmd == "/tokens":
            try:
                self.max_tokens = int(args)
                print(f"Max tokens set to: {self.max_tokens}")
            except ValueError:
                print("Invalid token count")
        
        elif cmd == "/history":
            if not self.conversation_history:
                print("No conversation history")
            else:
                print("\nConversation History:")
                print("-" * 40)
                for msg in self.conversation_history:
                    role = msg["role"].upper()
                    content = msg["content"]
                    if len(content) > 100:
                        content = content[:97] + "..."
                    print(f"{role}: {content}")
        
        elif cmd == "/clear":
            self.conversation_history = []
            print("Conversation history cleared")
        
        elif cmd == "/mcp":
            await self.handle_mcp_command(args)
        
        elif cmd == "/hide-thinking":
            self.show_thinking = False
            print("Thinking output hidden")
        
        elif cmd == "/show-thinking":
            self.show_thinking = True
            print("Thinking output shown")
        
        else:
            print(f"Unknown command: {cmd}")
    
    async def handle_mcp_command(self, args: str):
        """Handle MCP-related commands."""
        if not args:
            print("MCP commands: connect <cmd> <args>, disconnect, status")
            return
        
        parts = args.split()
        subcmd = parts[0].lower()
        
        if subcmd == "disconnect":
            if self.agent._mcp_connected:
                await self.agent.disconnect_mcp()
                print("Disconnected from MCP server")
            else:
                print("Not connected to MCP server")
        
        elif subcmd == "status":
            if self.agent._mcp_connected:
                context = await self.agent._mcp_client.get_context()
                print("MCP Status: Connected")
                print(context)
            else:
                print("MCP Status: Not connected")
        
        else:
            # Assume it's a connect command
            # Format: /mcp python -m my_server
            try:
                cmd_parts = args.split()
                if len(cmd_parts) < 1:
                    print("Usage: /mcp <command> [args...]")
                    return
                
                command = cmd_parts[0]
                cmd_args = cmd_parts[1:] if len(cmd_parts) > 1 else []
                
                print(f"Connecting to MCP server: {command} {' '.join(cmd_args)}")
                await self.agent.connect_mcp(command, cmd_args)
                print("Connected to MCP server")
                
                # Show available tools/resources
                context = await self.agent._mcp_client.get_context()
                print(context)
                
            except Exception as e:
                print(f"Failed to connect to MCP server: {e}")
    
    async def send_message(self, message: str):
        """Send a message to Claude and stream the response."""
        print("\nClaude:", end=" ", flush=True)
        
        try:
            # Track response for history
            response_parts = []
            thinking_parts = []
            
            async for event in self.agent.stream_response(
                system_prompt=self.system_prompt,
                user_prompt=message,
                thinking_budget=self.thinking_budget,
                max_tokens=self.max_tokens,
                conversation_history=self.conversation_history
            ):
                if event.type == StreamEventType.THINKING:
                    thinking_parts.append(event.content)
                    if self.show_thinking:
                        # Show thinking in a different color/format
                        print(f"\n[Thinking] {event.content}", end="", flush=True)
                
                elif event.type == StreamEventType.RESPONSE:
                    response_parts.append(event.content)
                    print(event.content, end="", flush=True)
                
                elif event.type == StreamEventType.ERROR:
                    print(f"\n[Error] {event.content}")
                    return
            
            print()  # New line after response
            
            # Add to conversation history
            self.conversation_history.append({"role": "user", "content": message})
            if response_parts:
                self.conversation_history.append({
                    "role": "assistant", 
                    "content": "".join(response_parts)
                })
            
            # Show thinking summary if hidden during streaming
            if thinking_parts and not self.show_thinking:
                print(f"\n[Thinking summary hidden - {len(thinking_parts)} tokens]")
            
        except Exception as e:
            print(f"\n[Error] {e}")


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Claude Agent CLI")
    parser.add_argument(
        "--api-key",
        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)"
    )
    parser.add_argument(
        "--model",
        default="claude-opus-4-20250514",
        help="Model to use (default: claude-opus-4-20250514)"
    )
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: No API key provided")
        print("Set ANTHROPIC_API_KEY environment variable or use --api-key")
        sys.exit(1)
    
    # Run CLI
    cli = ClaudeCLI(api_key=api_key, model=args.model)
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())