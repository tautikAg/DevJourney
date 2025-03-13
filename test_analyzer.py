#!/usr/bin/env python3
"""
Test script for the Cursor Chat History Analyzer

This script creates a sample data structure that mimics exported Cursor data
and runs the analyzer on it to verify functionality.
"""

import os
import json
import shutil
import tempfile
from pathlib import Path
import subprocess
import sys


def create_sample_data():
    """Create a sample data structure for testing the analyzer."""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp(prefix="cursor_test_data_")
    base_dir = Path(temp_dir)
    
    print(f"Creating sample data in: {base_dir}")
    
    # Create chat sessions structure
    chat_dir = base_dir / "chat_sessions" / "test_workspace_id" / "test_session_id"
    chat_dir.mkdir(parents=True)
    
    # Create state.json
    state_data = {
        "version": 1,
        "sessionId": "test_session_id",
        "linearHistory": [
            {
                "id": "message-1",
                "role": "user",
                "timestamp": 1623456789,
                "content": "How do I create a Python function?"
            },
            {
                "id": "message-2",
                "role": "assistant",
                "timestamp": 1623456800,
                "content": "Here's how you create a Python function..."
            }
        ],
        "linearHistoryIndex": 2,
        "recentSnapshot": {
            "workingSet": [
                {
                    "uri": "file:///test/project/main.py",
                    "state": 3,
                    "description": "Open Editor"
                }
            ]
        }
    }
    
    with open(chat_dir / "state.json", "w") as f:
        json.dump(state_data, f, indent=2)
    
    # Create history structure
    history_dir = base_dir / "history" / "test_history_id"
    history_dir.mkdir(parents=True)
    
    # Create entries.json
    entries_data = {
        "resource": "file:///test/project/main.py",
        "entries": [
            {
                "id": "entry1.json",
                "timestamp": 1623456789
            },
            {
                "id": "entry2.json",
                "timestamp": 1623456800
            }
        ]
    }
    
    with open(history_dir / "entries.json", "w") as f:
        json.dump(entries_data, f, indent=2)
    
    # Create entry files
    with open(history_dir / "entry1.json", "w") as f:
        f.write("def sample_function():\n    print('Hello, world!')\n")
    
    with open(history_dir / "entry2.json", "w") as f:
        f.write("def another_function(param):\n    return param * 2\n")
    
    # Create history summary
    with open(base_dir / "history" / "history_summary.txt", "w") as f:
        f.write("History Summary\n")
        f.write("Total directories: 1\n")
    
    # Create copilot chat structure
    copilot_dir = base_dir / "copilot_chat" / "test_workspace_id"
    copilot_dir.mkdir(parents=True)
    
    # Create metadata and preview files
    with open(copilot_dir / "metadata.txt", "w") as f:
        f.write("Workspace ID: test_workspace_id\n")
        f.write("File Size: 12345 bytes\n")
    
    with open(copilot_dir / "chunks_preview.txt", "w") as f:
        f.write('{"text":"<div>Sample HTML</div>","embedding":[0.1,0.2,0.3]}\n')
    
    # Create global storage structure
    global_dir = base_dir / "global_storage"
    global_dir.mkdir(parents=True)
    
    # Create storage.json
    storage_data = {
        "telemetry": {
            "id": "test-telemetry-id"
        },
        "backupWorkspaces": {
            "folders": [
                {
                    "folderUri": "file:///test/project"
                }
            ]
        }
    }
    
    with open(global_dir / "storage.json", "w") as f:
        json.dump(storage_data, f, indent=2)
    
    # Create database info
    with open(global_dir / "database_info.txt", "w") as f:
        f.write("Database Tables: ItemTable, cursorDiskKV\n")
    
    # Create a file with searchable content
    with open(base_dir / "searchable_file.txt", "w") as f:
        f.write("This file contains a searchable term: function definition example\n")
    
    return base_dir


def run_analyzer(data_dir, search_term=None):
    """Run the analyzer script on the sample data."""
    analyzer_script = Path(__file__).parent / "analyze_cursor_data.py"
    
    if not analyzer_script.exists():
        print(f"Error: Analyzer script not found at {analyzer_script}")
        return False
    
    cmd = [sys.executable, str(analyzer_script), str(data_dir)]
    
    if search_term:
        cmd.extend(["--search", search_term])
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("\n--- ANALYZER OUTPUT ---")
    print(result.stdout)
    
    if result.stderr:
        print("\n--- ERRORS ---")
        print(result.stderr)
    
    return result.returncode == 0


def cleanup(data_dir):
    """Clean up the temporary test data."""
    try:
        shutil.rmtree(data_dir)
        print(f"Cleaned up test data directory: {data_dir}")
    except Exception as e:
        print(f"Error cleaning up directory {data_dir}: {e}")


def main():
    """Run the test."""
    print("=== Testing Cursor Chat History Analyzer ===\n")
    
    # Create sample data
    data_dir = create_sample_data()
    
    try:
        # Run basic analysis
        print("\n=== Running basic analysis ===")
        success = run_analyzer(data_dir)
        
        if not success:
            print("Basic analysis test failed!")
            return
        
        # Run search analysis
        print("\n=== Running search analysis ===")
        search_success = run_analyzer(data_dir, "function definition")
        
        if not search_success:
            print("Search analysis test failed!")
            return
        
        print("\n=== All tests passed! ===")
    
    finally:
        # Clean up
        cleanup(data_dir)


if __name__ == "__main__":
    main() 