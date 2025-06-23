#!/usr/bin/env python3
"""Launcher script for Claude Agent Chat Interface."""

import os
import sys
import time
import webbrowser
import subprocess
import argparse
import signal
from pathlib import Path

def main():
    """Run the chat interface."""
    parser = argparse.ArgumentParser(description="Launch Claude Agent Chat Interface")
    parser.add_argument('--port', type=int, default=8080, help='Port to run server on (default: 8080)')
    parser.add_argument('--no-browser', action='store_true', help='Do not open browser automatically')
    parser.add_argument('--host', default='localhost', help='Host to bind to (default: localhost)')
    args = parser.parse_args()
    
    # Check if required files exist
    script_dir = Path(__file__).parent
    server_file = script_dir / 'chat_server.py'
    html_file = script_dir / 'chat_interface.html'
    
    if not server_file.exists():
        print(f"Error: {server_file} not found")
        sys.exit(1)
    
    if not html_file.exists():
        print(f"Error: {html_file} not found")
        sys.exit(1)
    
    # Start the server
    print(f"Starting Claude Agent Chat Interface on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop\n")
    
    server_process = None
    
    try:
        # Start server in subprocess
        server_process = subprocess.Popen(
            [sys.executable, str(server_file), '--port', str(args.port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Wait a moment for server to start
        time.sleep(1)
        
        # Check if server started successfully
        if server_process.poll() is not None:
            print("Error: Server failed to start")
            sys.exit(1)
        
        # Open browser if requested
        if not args.no_browser:
            url = f"http://{args.host}:{args.port}"
            print(f"Opening browser at {url}")
            webbrowser.open(url)
        
        print("\nServer is running. Logs:")
        print("-" * 50)
        
        # Stream server output
        while True:
            output = server_process.stdout.readline()
            if output:
                print(output.strip())
            elif server_process.poll() is not None:
                break
                
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        if server_process:
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
            print("Server stopped")


if __name__ == "__main__":
    main()