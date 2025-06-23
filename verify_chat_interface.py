#!/usr/bin/env python3
"""Quick verification script for the chat interface."""

import os
import sys

def verify_installation():
    """Verify all components are in place."""
    print("Claude Agent Chat Interface Verification")
    print("=" * 50)
    
    # Check files
    required_files = {
        'chat_server.py': 'Chat server',
        'chat_interface.html': 'Web interface',
        'run_chat.py': 'Launcher script',
        'src/claude_agent/agent.py': 'Claude agent core',
        'CHAT_INTERFACE_README.md': 'Documentation'
    }
    
    all_good = True
    print("\n📁 Checking required files:")
    for file, desc in required_files.items():
        if os.path.exists(file):
            print(f"  ✅ {desc}: {file}")
        else:
            print(f"  ❌ {desc}: {file} (NOT FOUND)")
            all_good = False
    
    # Check Python version
    print(f"\n🐍 Python version: {sys.version.split()[0]}")
    if sys.version_info >= (3, 9):
        print("  ✅ Python 3.9+ detected")
    else:
        print("  ❌ Python 3.9+ required")
        all_good = False
    
    # Check virtual environment
    print("\n🔧 Environment:")
    if os.environ.get('VIRTUAL_ENV'):
        print(f"  ✅ Virtual environment active: {os.environ['VIRTUAL_ENV']}")
    else:
        print("  ⚠️  No virtual environment detected (recommended)")
    
    # Check imports
    print("\n📦 Checking imports:")
    try:
        import claude_agent
        print("  ✅ claude_agent package")
    except ImportError:
        print("  ❌ claude_agent package (run: pip install -e .)")
        all_good = False
    
    try:
        import httpx
        print("  ✅ httpx library")
    except ImportError:
        print("  ❌ httpx library (run: pip install httpx)")
        all_good = False
    
    # Instructions
    print("\n" + "=" * 50)
    if all_good:
        print("✅ All checks passed!")
        print("\n🚀 To start the chat interface:")
        print("   python run_chat.py")
        print("\n📖 For more information:")
        print("   See CHAT_INTERFACE_README.md")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print("\nQuick fix:")
        print("1. Activate virtual environment: source venv/bin/activate")
        print("2. Install package: pip install -e .")
    
    return all_good


def test_imports():
    """Test that imports work correctly."""
    print("\n🧪 Testing imports...")
    try:
        from chat_server import ChatHandler, sessions
        print("  ✅ chat_server imports")
        
        from claude_agent.agent import ClaudeAgent, StreamEventType
        print("  ✅ claude_agent imports")
        
        return True
    except Exception as e:
        print(f"  ❌ Import error: {e}")
        return False


if __name__ == "__main__":
    success = verify_installation()
    
    if success:
        test_imports()
    
    sys.exit(0 if success else 1)