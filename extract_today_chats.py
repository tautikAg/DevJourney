#!/usr/bin/env python3
"""
Extract Today's Cursor Chat History for Notion Integration

This script extracts today's chat history from Cursor and formats it for integration with Notion.
It can be run daily to keep your Notion database updated with your latest development activities.
"""

import os
import json
import shutil
import sqlite3
import platform
import argparse
import tempfile
from datetime import datetime, timedelta
from pathlib import Path


def get_cursor_data_path():
    """Get the path to Cursor application data based on the operating system."""
    system = platform.system()
    home = Path.home()
    
    if system == "Darwin":  # macOS
        return home / "Library" / "Application Support" / "Cursor"
    elif system == "Windows":
        return Path(os.environ.get("APPDATA")) / "Cursor"
    elif system == "Linux":
        return home / ".config" / "Cursor"
    else:
        raise ValueError(f"Unsupported operating system: {system}")


def create_temp_directory():
    """Create a temporary directory for processing data."""
    temp_dir = Path(tempfile.mkdtemp(prefix="cursor_today_"))
    return temp_dir


def is_today(timestamp):
    """Check if a timestamp is from today."""
    if isinstance(timestamp, int):
        # Convert milliseconds to seconds if needed
        if timestamp > 1600000000000:  # If timestamp is in milliseconds
            timestamp = timestamp / 1000
        
        date = datetime.fromtimestamp(timestamp)
    elif isinstance(timestamp, str):
        try:
            date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            try:
                date = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError:
                return False
    else:
        return False
    
    today = datetime.now().date()
    return date.date() == today


def extract_chat_sessions(cursor_path, output_dir):
    """Extract today's chat editing sessions."""
    workspace_storage = cursor_path / "User" / "workspaceStorage"
    today_chats = []
    
    if not workspace_storage.exists():
        print(f"Workspace storage directory not found: {workspace_storage}")
        return today_chats
    
    print("Extracting today's chat sessions...")
    
    for workspace_dir in workspace_storage.iterdir():
        if not workspace_dir.is_dir():
            continue
        
        chat_dir = workspace_dir / "chatEditingSessions"
        if not chat_dir.exists():
            continue
        
        for session_dir in chat_dir.iterdir():
            if not session_dir.is_dir():
                continue
            
            # Check state.json for today's date
            state_file = session_dir / "state.json"
            if state_file.exists():
                try:
                    with open(state_file, 'r') as f:
                        state_data = json.load(f)
                    
                    # Check if this session has history items from today
                    today_history_items = []
                    
                    if "linearHistory" in state_data and state_data["linearHistory"]:
                        for item in state_data["linearHistory"]:
                            # Check if the item has a timestamp and it's from today
                            if isinstance(item, dict) and "timestamp" in item and is_today(item["timestamp"]):
                                today_history_items.append(item)
                            # Some sessions use requestId format
                            elif isinstance(item, dict) and "requestId" in item:
                                # If no timestamp, assume it's recent and include it
                                today_history_items.append(item)
                    
                    if today_history_items:
                        # Get workspace info
                        workspace_info = {
                            "workspace_id": workspace_dir.name,
                            "session_id": session_dir.name
                        }
                        
                        # Get working set files
                        files = []
                        if "recentSnapshot" in state_data and "workingSet" in state_data["recentSnapshot"]:
                            working_set = state_data["recentSnapshot"]["workingSet"]
                            for item in working_set:
                                if isinstance(item, list) and len(item) > 0:
                                    files.append(item[0])  # Format: ['file:///path/to/file', {...}]
                                elif isinstance(item, dict) and "uri" in item:
                                    files.append(item["uri"])
                        
                        # Create a chat session entry
                        chat_session = {
                            "workspace": workspace_info,
                            "history_items": today_history_items,
                            "files": files
                        }
                        
                        today_chats.append(chat_session)
                        
                        # Save to output directory for reference
                        session_dir_output = output_dir / "chat_sessions" / workspace_dir.name / session_dir.name
                        session_dir_output.mkdir(parents=True, exist_ok=True)
                        
                        with open(session_dir_output / "session_data.json", 'w') as f:
                            json.dump(chat_session, f, indent=2)
                        
                except Exception as e:
                    print(f"Error processing state file {state_file}: {e}")
    
    print(f"Found {len(today_chats)} chat sessions from today")
    return today_chats


def extract_history_entries(cursor_path, output_dir):
    """Extract today's history entries."""
    history_dir = cursor_path / "User" / "History"
    today_entries = []
    
    if not history_dir.exists():
        print(f"History directory not found: {history_dir}")
        return today_entries
    
    print("Extracting today's history entries...")
    
    for history_subdir in history_dir.iterdir():
        if not history_subdir.is_dir():
            continue
        
        # Check entries.json for today's entries
        entries_file = history_subdir / "entries.json"
        if entries_file.exists():
            try:
                with open(entries_file, 'r') as f:
                    entries_data = json.load(f)
                
                if "entries" in entries_data:
                    today_subdir_entries = []
                    
                    for entry in entries_data["entries"]:
                        if "timestamp" in entry and is_today(entry["timestamp"]):
                            # Get the entry content
                            entry_content = None
                            entry_id = entry.get("id")
                            
                            if entry_id:
                                entry_file = history_subdir / entry_id
                                if entry_file.exists():
                                    try:
                                        with open(entry_file, 'r', errors='ignore') as f:
                                            entry_content = f.read()
                                    except Exception as e:
                                        print(f"Error reading entry file {entry_file}: {e}")
                            
                            # Add to today's entries
                            today_entry = {
                                "entry_info": entry,
                                "content": entry_content,
                                "resource": entries_data.get("resource", "")
                            }
                            
                            today_subdir_entries.append(today_entry)
                    
                    if today_subdir_entries:
                        today_entries.extend(today_subdir_entries)
                        
                        # Save to output directory for reference
                        subdir_output = output_dir / "history" / history_subdir.name
                        subdir_output.mkdir(parents=True, exist_ok=True)
                        
                        with open(subdir_output / "today_entries.json", 'w') as f:
                            json.dump(today_subdir_entries, f, indent=2)
            
            except Exception as e:
                print(f"Error processing entries file {entries_file}: {e}")
    
    print(f"Found {len(today_entries)} history entries from today")
    return today_entries


def format_for_notion(chat_sessions, history_entries):
    """Format the extracted data for Notion integration."""
    print("Formatting data for Notion integration...")
    
    # Create a structure that will be easy to import into Notion
    notion_data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "chat_sessions": [],
        "edited_files": [],
        "code_snippets": []
    }
    
    # Process chat sessions
    for session in chat_sessions:
        session_summary = {
            "workspace_id": session["workspace"]["workspace_id"],
            "session_id": session["workspace"]["session_id"],
            "history_count": len(session["history_items"]),
            "files": session["files"]
        }
        
        # Extract user questions and AI responses
        conversations = []
        for item in session["history_items"]:
            if isinstance(item, dict):
                if "role" in item and "content" in item:
                    conversations.append({
                        "role": item["role"],
                        "content": item["content"][:500] + "..." if len(item["content"]) > 500 else item["content"]
                    })
                elif "requestId" in item:
                    # For requestId format, we don't have clear user/assistant distinction
                    conversations.append({
                        "requestId": item["requestId"],
                        "entries_count": len(item.get("entries", []))
                    })
        
        session_summary["conversations"] = conversations
        notion_data["chat_sessions"].append(session_summary)
        
        # Add files to the edited files list
        for file in session["files"]:
            if file not in notion_data["edited_files"]:
                notion_data["edited_files"].append(file)
    
    # Process history entries
    for entry in history_entries:
        resource = entry["resource"]
        content = entry["content"]
        
        if resource and resource not in notion_data["edited_files"]:
            notion_data["edited_files"].append(resource)
        
        if content:
            # Try to identify code snippets
            if content.strip().startswith(("def ", "class ", "import ", "from ", "function", "const ", "let ", "var ")):
                snippet = {
                    "file": resource,
                    "language": resource.split(".")[-1] if "." in resource else "text",
                    "snippet": content[:500] + "..." if len(content) > 500 else content
                }
                notion_data["code_snippets"].append(snippet)
    
    # Save the formatted data
    return notion_data


def save_notion_data(notion_data, output_dir):
    """Save the formatted Notion data to a JSON file."""
    notion_file = output_dir / "notion_data.json"
    
    with open(notion_file, 'w') as f:
        json.dump(notion_data, f, indent=2)
    
    print(f"Notion data saved to: {notion_file}")
    return notion_file


def main():
    parser = argparse.ArgumentParser(description="Extract today's Cursor chat history for Notion integration")
    parser.add_argument("--output", "-o", help="Output directory for extracted data")
    args = parser.parse_args()
    
    try:
        cursor_path = get_cursor_data_path()
        print(f"Cursor data path: {cursor_path}")
        
        if not cursor_path.exists():
            print(f"Cursor data directory not found: {cursor_path}")
            return
        
        # Create output directory
        if args.output:
            output_dir = Path(args.output)
        else:
            today = datetime.now().strftime("%Y%m%d")
            output_dir = Path.cwd() / f"cursor_today_{today}"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Saving data to: {output_dir}")
        
        # Extract today's data
        chat_sessions = extract_chat_sessions(cursor_path, output_dir)
        history_entries = extract_history_entries(cursor_path, output_dir)
        
        # Format for Notion
        notion_data = format_for_notion(chat_sessions, history_entries)
        
        # Save Notion data
        notion_file = save_notion_data(notion_data, output_dir)
        
        print("\nExtraction completed successfully!")
        print(f"Today's chat history extracted and formatted for Notion integration.")
        print(f"Use the data in {notion_file} to update your Notion database.")
        
        # Print summary
        print("\nSummary:")
        print(f"- Chat Sessions: {len(notion_data['chat_sessions'])}")
        print(f"- Edited Files: {len(notion_data['edited_files'])}")
        print(f"- Code Snippets: {len(notion_data['code_snippets'])}")
        
    except Exception as e:
        print(f"Error during extraction: {e}")


if __name__ == "__main__":
    main() 