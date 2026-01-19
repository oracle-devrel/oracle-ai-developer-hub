#!/usr/bin/env python3
"""
A2A Protocol Test Runner

This script runs the A2A protocol tests and provides a simple interface
for testing the implementation.
"""

import sys
import asyncio
import subprocess
from pathlib import Path
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_tests():
    """Run A2A protocol tests"""
    print("🧪 Running A2A Protocol Tests")
    print("=" * 50)
    
    try:
        # Run pytest
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "test_a2a.py", 
            "-v", 
            "--tb=short"
        ], capture_output=True, text=True)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ All tests passed!")
            return True
        else:
            print("❌ Some tests failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error running tests: {str(e)}")
        return False

def run_quick_test():
    """Run a quick integration test"""
    print("\n🚀 Running Quick Integration Test")
    print("=" * 50)
    
    try:
        # Import and test basic functionality
        from src.a2a_models import A2ARequest, A2AResponse
        from src.agent_card import get_agent_card
        from src.task_manager import TaskManager
        from src.agent_registry import AgentRegistry
        
        # Test agent card
        print("Testing agent card...")
        card = get_agent_card()
        assert "agent_id" in card
        assert card["agent_id"] == "agentic_rag_v1"
        print("✅ Agent card test passed")
        
        # Test task manager
        print("Testing task manager...")
        task_manager = TaskManager()
        print("✅ Task manager created")
        
        # Test agent registry
        print("Testing agent registry...")
        registry = AgentRegistry()
        print("✅ Agent registry created")
        
        # Test A2A models
        print("Testing A2A models...")
        request = A2ARequest(method="test.method", params={})
        assert request.jsonrpc == "2.0"
        print("✅ A2A models test passed")
        
        print("\n✅ Quick integration test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Quick test failed: {str(e)}")
        return False

def main():
    """Main test runner"""
    print("A2A Protocol Test Suite")
    print("=" * 50)
    
    # Run quick test first
    if not run_quick_test():
        print("❌ Quick test failed, skipping full test suite")
        return False
    
    # Run full test suite
    if not run_tests():
        print("❌ Full test suite failed")
        return False
    
    print("\n🎉 All tests completed successfully!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
