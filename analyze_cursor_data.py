#!/usr/bin/env python3
"""
Cursor Chat History Analyzer

This script analyzes exported Cursor chat history data to extract meaningful information.
It should be run after using export_cursor_data.py to export the data.
"""

import os
import json
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime


def find_chat_sessions(export_dir):
    """Find and analyze chat sessions in the exported data."""
    chat_sessions_dir = Path(export_dir) / "chat_sessions"
    if not chat_sessions_dir.exists():
        print("Chat sessions directory not found.")
        return
    
    print("\n=== Chat Sessions Analysis ===\n")
    
    session_count = 0
    for workspace_dir in chat_sessions_dir.iterdir():
        if not workspace_dir.is_dir():
            continue
        
        print(f"Workspace: {workspace_dir.name}")
        
        for session_dir in workspace_dir.iterdir():
            if not session_dir.is_dir():
                continue
            
            session_count += 1
            print(f"  Session: {session_dir.name}")
            
            # Analyze state.json
            state_file = session_dir / "state.json"
            if state_file.exists():
                try:
                    with open(state_file, 'r') as f:
                        state_data = json.load(f)
                    
                    if "linearHistory" in state_data and state_data["linearHistory"]:
                        print(f"    History Items: {len(state_data['linearHistory'])}")
                        
                        # Extract some sample history items
                        for i, item in enumerate(state_data["linearHistory"][:3]):
                            print(f"    History Item {i+1}:")
                            if isinstance(item, dict):
                                for key, value in item.items():
                                    if key != "content" and key != "embedding":  # Skip large fields
                                        print(f"      {key}: {value}")
                    else:
                        print("    No history items found")
                    
                    # Check for working set files
                    if "recentSnapshot" in state_data and "workingSet" in state_data["recentSnapshot"]:
                        working_set = state_data["recentSnapshot"]["workingSet"]
                        if working_set:
                            print(f"    Working Set Files: {len(working_set)}")
                            for i, item in enumerate(working_set[:3]):  # Show up to 3 files
                                if "uri" in item:
                                    print(f"      File {i+1}: {item['uri']}")
                except Exception as e:
                    print(f"    Error analyzing state file: {e}")
            
            print("")
    
    print(f"Total Chat Sessions: {session_count}")


def analyze_history(export_dir):
    """Analyze history data in the exported data."""
    history_dir = Path(export_dir) / "history"
    if not history_dir.exists():
        print("History directory not found.")
        return
    
    print("\n=== History Data Analysis ===\n")
    
    # Look for the summary file
    summary_file = history_dir / "history_summary.txt"
    if summary_file.exists():
        print("History summary file found. Key statistics:")
        
        # Count directories and entries
        dir_count = sum(1 for _ in history_dir.iterdir() if _.is_dir())
        print(f"Total history directories: {dir_count}")
        
        # Sample some entries
        sample_count = 0
        for subdir in history_dir.iterdir():
            if not subdir.is_dir() or sample_count >= 3:
                continue
            
            entries_file = subdir / "entries.json"
            if entries_file.exists():
                try:
                    with open(entries_file, 'r') as f:
                        entries_data = json.load(f)
                    
                    if "resource" in entries_data:
                        print(f"\nDirectory: {subdir.name}")
                        print(f"Resource: {entries_data['resource']}")
                        
                        if "entries" in entries_data:
                            print(f"Entries: {len(entries_data['entries'])}")
                            
                            # Show a few entries
                            for i, entry in enumerate(entries_data["entries"][:2]):
                                print(f"  Entry {i+1}:")
                                for key, value in entry.items():
                                    print(f"    {key}: {value}")
                                
                                # Try to read the entry file
                                if "id" in entry:
                                    entry_file = subdir / entry["id"]
                                    if entry_file.exists():
                                        try:
                                            with open(entry_file, 'r') as f:
                                                content = f.read(200)  # Read first 200 chars
                                            print(f"    Content Preview: {content}...")
                                        except Exception:
                                            print("    Content: [Binary or non-text data]")
                    
                    sample_count += 1
                except Exception as e:
                    print(f"Error analyzing entries file {entries_file}: {e}")
    else:
        print("History summary file not found.")


def analyze_copilot_chat(export_dir):
    """Analyze GitHub Copilot chat data in the exported data."""
    copilot_dir = Path(export_dir) / "copilot_chat"
    if not copilot_dir.exists():
        print("Copilot chat directory not found.")
        return
    
    print("\n=== GitHub Copilot Chat Analysis ===\n")
    
    workspace_count = 0
    for workspace_dir in copilot_dir.iterdir():
        if not workspace_dir.is_dir():
            continue
        
        workspace_count += 1
        print(f"Workspace: {workspace_dir.name}")
        
        # Check for metadata
        metadata_file = workspace_dir / "metadata.txt"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    metadata = f.read()
                print(f"  Metadata:\n    {metadata.replace('\n', '\n    ')}")
            except Exception as e:
                print(f"  Error reading metadata: {e}")
        
        # Check for chunks preview
        preview_file = workspace_dir / "chunks_preview.txt"
        if preview_file.exists():
            try:
                with open(preview_file, 'r') as f:
                    preview = f.read(300)  # Read first 300 chars
                print(f"  Preview Sample:\n    {preview.replace('\n', '\n    ')}...")
            except Exception as e:
                print(f"  Error reading preview: {e}")
        
        print("")
    
    print(f"Total Copilot Chat Workspaces: {workspace_count}")


def analyze_global_storage(export_dir):
    """Analyze global storage data in the exported data."""
    global_dir = Path(export_dir) / "global_storage"
    if not global_dir.exists():
        print("Global storage directory not found.")
        return
    
    print("\n=== Global Storage Analysis ===\n")
    
    # Check for storage.json
    storage_file = global_dir / "storage.json"
    if storage_file.exists():
        try:
            with open(storage_file, 'r') as f:
                storage_data = json.load(f)
            
            print("Storage.json contents:")
            
            # Print top-level keys
            print("  Top-level keys:")
            for key in storage_data.keys():
                print(f"    - {key}")
            
            # Check for specific interesting keys
            if "backupWorkspaces" in storage_data and "folders" in storage_data["backupWorkspaces"]:
                print("\n  Workspace folders:")
                for folder in storage_data["backupWorkspaces"]["folders"]:
                    if "folderUri" in folder:
                        print(f"    - {folder['folderUri']}")
        except Exception as e:
            print(f"Error analyzing storage.json: {e}")
    
    # Check for database info
    db_info_file = global_dir / "database_info.txt"
    if db_info_file.exists():
        try:
            with open(db_info_file, 'r') as f:
                db_info = f.read(500)  # Read first 500 chars
            print(f"\nDatabase Info Preview:\n{db_info}...")
        except Exception as e:
            print(f"Error reading database info: {e}")


def search_for_text(export_dir, search_text):
    """Search for specific text in the exported data."""
    if not search_text:
        return
    
    print(f"\n=== Searching for: '{search_text}' ===\n")
    
    export_path = Path(export_dir)
    matches = []
    
    # Walk through all files in the export directory
    for root, _, files in os.walk(export_path):
        for file in files:
            file_path = Path(root) / file
            
            # Skip binary files and very large files
            if file_path.suffix.lower() in ['.db', '.vscdb', '.backup'] or file_path.stat().st_size > 10_000_000:
                continue
            
            try:
                with open(file_path, 'r', errors='ignore') as f:
                    content = f.read()
                
                if search_text.lower() in content.lower():
                    rel_path = file_path.relative_to(export_path)
                    matches.append(str(rel_path))
                    
                    # Find the context around the match
                    lower_content = content.lower()
                    pos = lower_content.find(search_text.lower())
                    start = max(0, pos - 50)
                    end = min(len(content), pos + len(search_text) + 50)
                    context = content[start:end]
                    
                    print(f"Match in: {rel_path}")
                    print(f"Context: ...{context}...")
                    print("")
            except Exception:
                # Skip files that can't be read as text
                pass
    
    print(f"Found {len(matches)} matches for '{search_text}'")


def main():
    parser = argparse.ArgumentParser(description="Analyze exported Cursor chat history data")
    parser.add_argument("export_dir", help="Directory containing exported Cursor data")
    parser.add_argument("--search", "-s", help="Search for specific text in the exported data")
    args = parser.parse_args()
    
    export_dir = args.export_dir
    if not os.path.isdir(export_dir):
        print(f"Error: {export_dir} is not a valid directory")
        return
    
    print(f"Analyzing Cursor data in: {export_dir}")
    
    # Run the analysis functions
    find_chat_sessions(export_dir)
    analyze_history(export_dir)
    analyze_copilot_chat(export_dir)
    analyze_global_storage(export_dir)
    
    # Search for text if specified
    if args.search:
        search_for_text(export_dir, args.search)
    
    print("\nAnalysis complete!")


if __name__ == "__main__":
    main() 