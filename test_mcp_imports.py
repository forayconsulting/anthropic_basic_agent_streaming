#!/usr/bin/env python3
"""Test MCP imports and basic functionality."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("Testing MCP imports...")
    
    from mcp import ClientSession, StdioServerParameters
    print("✅ Imported ClientSession, StdioServerParameters")
    
    from mcp.client.stdio import stdio_client
    print("✅ Imported stdio_client")
    
    # Check what's in the mcp module
    import mcp
    print("\nMCP module attributes:")
    for attr in dir(mcp):
        if not attr.startswith('_'):
            print(f"  - {attr}")
    
    # Check stdio_client
    import mcp.client.stdio
    print("\nMCP client.stdio attributes:")
    for attr in dir(mcp.client.stdio):
        if not attr.startswith('_'):
            print(f"  - {attr}")
            
    print("\n✅ All imports successful")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nYou may need to install the MCP package:")
    print("pip install mcp")