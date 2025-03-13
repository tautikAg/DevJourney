#!/usr/bin/env python3
"""
Cursor Chat History Exporter

This script exports Cursor chat history and related data from your local machine.
It gathers data from various locations and organizes it into a more accessible format.
"""

import os
import json
import shutil
import sqlite3
import platform
import argparse
from datetime import datetime
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


def create_export_directory(base_dir=None):
    """Create a directory for exporting data."""
    if base_dir:
        export_dir = Path(base_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_dir = Path.cwd() / f"cursor_data_export_{timestamp}"
    
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir


def export_chat_sessions(cursor_path, export_dir):
    """Export chat editing sessions data."""
    workspace_storage = cursor_path / "User" / "workspaceStorage"
    chat_sessions_dir = export_dir / "chat_sessions"
    chat_sessions_dir.mkdir(exist_ok=True)
    
    if not workspace_storage.exists():
        print(f"Workspace storage directory not found: {workspace_storage}")
        return
    
    print("Exporting chat editing sessions...")
    
    # Track the number of sessions found
    session_count = 0
    
    for workspace_dir in workspace_storage.iterdir():
        if not workspace_dir.is_dir():
            continue
        
        chat_dir = workspace_dir / "chatEditingSessions"
        if not chat_dir.exists():
            continue
        
        workspace_export_dir = chat_sessions_dir / workspace_dir.name
        workspace_export_dir.mkdir(exist_ok=True)
        
        for session_dir in chat_dir.iterdir():
            if not session_dir.is_dir():
                continue
            
            session_export_dir = workspace_export_dir / session_dir.name
            session_export_dir.mkdir(exist_ok=True)
            
            # Export state.json
            state_file = session_dir / "state.json"
            if state_file.exists():
                try:
                    with open(state_file, 'r') as f:
                        state_data = json.load(f)
                    
                    with open(session_export_dir / "state.json", 'w') as f:
                        json.dump(state_data, f, indent=2)
                    
                    # Also save a text summary
                    with open(session_export_dir / "summary.txt", 'w') as f:
                        f.write(f"Chat Session: {session_dir.name}\n")
                        f.write(f"Workspace: {workspace_dir.name}\n\n")
                        
                        if "linearHistory" in state_data and state_data["linearHistory"]:
                            f.write(f"History Items: {len(state_data['linearHistory'])}\n")
                        else:
                            f.write("No history items found\n")
                        
                        if "recentSnapshot" in state_data and state_data["recentSnapshot"]:
                            f.write("\nRecent Snapshot:\n")
                            f.write(json.dumps(state_data["recentSnapshot"], indent=2))
                except Exception as e:
                    print(f"Error processing state file {state_file}: {e}")
            
            # Export contents directory
            contents_dir = session_dir / "contents"
            if contents_dir.exists() and contents_dir.is_dir():
                contents_export_dir = session_export_dir / "contents"
                contents_export_dir.mkdir(exist_ok=True)
                
                for content_file in contents_dir.iterdir():
                    try:
                        shutil.copy2(content_file, contents_export_dir)
                    except Exception as e:
                        print(f"Error copying content file {content_file}: {e}")
            
            session_count += 1
    
    print(f"Exported {session_count} chat sessions")


def export_history(cursor_path, export_dir):
    """Export history data."""
    history_dir = cursor_path / "User" / "History"
    history_export_dir = export_dir / "history"
    history_export_dir.mkdir(exist_ok=True)
    
    if not history_dir.exists():
        print(f"History directory not found: {history_dir}")
        return
    
    print("Exporting history data...")
    
    # Create a summary file
    summary_file = history_export_dir / "history_summary.txt"
    with open(summary_file, 'w') as summary:
        summary.write("Cursor History Summary\n")
        summary.write("====================\n\n")
        
        # Track the number of history entries found
        entry_count = 0
        
        for history_subdir in history_dir.iterdir():
            if not history_subdir.is_dir():
                continue
            
            subdir_export = history_export_dir / history_subdir.name
            subdir_export.mkdir(exist_ok=True)
            
            # Look for entries.json
            entries_file = history_subdir / "entries.json"
            if entries_file.exists():
                try:
                    with open(entries_file, 'r') as f:
                        entries_data = json.load(f)
                    
                    with open(subdir_export / "entries.json", 'w') as f:
                        json.dump(entries_data, f, indent=2)
                    
                    # Add to summary
                    summary.write(f"Directory: {history_subdir.name}\n")
                    if "resource" in entries_data:
                        summary.write(f"Resource: {entries_data['resource']}\n")
                    if "entries" in entries_data:
                        summary.write(f"Entries: {len(entries_data['entries'])}\n")
                        for entry in entries_data["entries"]:
                            entry_id = entry.get("id", "unknown")
                            timestamp = entry.get("timestamp", "unknown")
                            source = entry.get("source", "unknown")
                            summary.write(f"  - ID: {entry_id}, Timestamp: {timestamp}, Source: {source}\n")
                            
                            # Copy the entry file if it exists
                            entry_file = history_subdir / entry_id
                            if entry_file.exists():
                                try:
                                    shutil.copy2(entry_file, subdir_export)
                                    entry_count += 1
                                except Exception as e:
                                    print(f"Error copying entry file {entry_file}: {e}")
                    
                    summary.write("\n")
                except Exception as e:
                    print(f"Error processing entries file {entries_file}: {e}")
            
            # Copy other files in the directory
            for file in history_subdir.iterdir():
                if file.is_file() and file.name != "entries.json":
                    try:
                        shutil.copy2(file, subdir_export)
                    except Exception as e:
                        print(f"Error copying history file {file}: {e}")
    
    print(f"Exported history data with {entry_count} entries")


def export_copilot_chat(cursor_path, export_dir):
    """Export GitHub Copilot chat data."""
    workspace_storage = cursor_path / "User" / "workspaceStorage"
    copilot_export_dir = export_dir / "copilot_chat"
    copilot_export_dir.mkdir(exist_ok=True)
    
    if not workspace_storage.exists():
        print(f"Workspace storage directory not found: {workspace_storage}")
        return
    
    print("Exporting GitHub Copilot chat data...")
    
    # Track the number of copilot chat files found
    file_count = 0
    
    for workspace_dir in workspace_storage.iterdir():
        if not workspace_dir.is_dir():
            continue
        
        copilot_dir = workspace_dir / "GitHub.copilot-chat"
        if not copilot_dir.exists():
            continue
        
        workspace_export_dir = copilot_export_dir / workspace_dir.name
        workspace_export_dir.mkdir(exist_ok=True)
        
        # Export workspace-chunks.json
        chunks_file = copilot_dir / "workspace-chunks.json"
        if chunks_file.exists():
            try:
                # For large files, we'll extract key information instead of copying the whole file
                with open(chunks_file, 'r') as f:
                    # Read the first 1000 characters to get a sense of the structure
                    preview = f.read(1000)
                
                with open(workspace_export_dir / "chunks_preview.txt", 'w') as f:
                    f.write(f"Preview of {chunks_file}:\n\n")
                    f.write(preview)
                    f.write("\n...(file truncated)...\n")
                
                # Also create a metadata file
                file_size = chunks_file.stat().st_size
                with open(workspace_export_dir / "metadata.txt", 'w') as f:
                    f.write(f"File: {chunks_file}\n")
                    f.write(f"Size: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)\n")
                    f.write(f"Last Modified: {datetime.fromtimestamp(chunks_file.stat().st_mtime)}\n")
                
                file_count += 1
            except Exception as e:
                print(f"Error processing chunks file {chunks_file}: {e}")
    
    print(f"Exported {file_count} Copilot chat files")


def export_global_storage(cursor_path, export_dir):
    """Export global storage data."""
    global_storage = cursor_path / "User" / "globalStorage"
    global_export_dir = export_dir / "global_storage"
    global_export_dir.mkdir(exist_ok=True)
    
    if not global_storage.exists():
        print(f"Global storage directory not found: {global_storage}")
        return
    
    print("Exporting global storage data...")
    
    # Export storage.json
    storage_file = global_storage / "storage.json"
    if storage_file.exists():
        try:
            with open(storage_file, 'r') as f:
                storage_data = json.load(f)
            
            with open(global_export_dir / "storage.json", 'w') as f:
                json.dump(storage_data, f, indent=2)
        except Exception as e:
            print(f"Error processing storage file {storage_file}: {e}")
    
    # Export SQLite database information
    db_file = global_storage / "state.vscdb"
    if db_file.exists():
        try:
            # Create a metadata file with table information
            with open(global_export_dir / "database_info.txt", 'w') as f:
                f.write(f"Database: {db_file}\n")
                f.write(f"Size: {db_file.stat().st_size} bytes ({db_file.stat().st_size / 1024 / 1024:.2f} MB)\n")
                f.write(f"Last Modified: {datetime.fromtimestamp(db_file.stat().st_mtime)}\n\n")
                
                # Connect to the database and get table information
                conn = sqlite3.connect(str(db_file))
                cursor = conn.cursor()
                
                # Get list of tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                f.write("Tables:\n")
                for table in tables:
                    table_name = table[0]
                    f.write(f"- {table_name}\n")
                    
                    # Get table schema
                    cursor.execute(f"PRAGMA table_info({table_name});")
                    columns = cursor.fetchall()
                    
                    f.write("  Columns:\n")
                    for column in columns:
                        f.write(f"  - {column[1]} ({column[2]})\n")
                    
                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                    row_count = cursor.fetchone()[0]
                    f.write(f"  Row count: {row_count}\n\n")
                
                conn.close()
        except Exception as e:
            print(f"Error processing database file {db_file}: {e}")
    
    # Copy other files
    for file in global_storage.iterdir():
        if file.is_file() and file.name not in ["storage.json", "state.vscdb", "state.vscdb.backup"]:
            try:
                shutil.copy2(file, global_export_dir)
            except Exception as e:
                print(f"Error copying global storage file {file}: {e}")


def create_summary(export_dir):
    """Create a summary of all exported data."""
    summary_file = export_dir / "export_summary.txt"
    
    with open(summary_file, 'w') as f:
        f.write("Cursor Data Export Summary\n")
        f.write("=========================\n\n")
        f.write(f"Export Date: {datetime.now()}\n")
        f.write(f"System: {platform.system()} {platform.release()}\n\n")
        
        # Chat Sessions
        chat_sessions_dir = export_dir / "chat_sessions"
        if chat_sessions_dir.exists():
            workspace_count = sum(1 for _ in chat_sessions_dir.iterdir() if _.is_dir())
            f.write(f"Chat Sessions: {workspace_count} workspaces\n")
        
        # History
        history_dir = export_dir / "history"
        if history_dir.exists():
            history_count = sum(1 for _ in history_dir.iterdir() if _.is_dir())
            f.write(f"History: {history_count} directories\n")
        
        # Copilot Chat
        copilot_dir = export_dir / "copilot_chat"
        if copilot_dir.exists():
            copilot_count = sum(1 for _ in copilot_dir.iterdir() if _.is_dir())
            f.write(f"Copilot Chat: {copilot_count} workspaces\n")
        
        # Global Storage
        global_dir = export_dir / "global_storage"
        if global_dir.exists():
            global_count = sum(1 for _ in global_dir.iterdir() if _.is_file())
            f.write(f"Global Storage: {global_count} files\n")


def main():
    parser = argparse.ArgumentParser(description="Export Cursor chat history and related data")
    parser.add_argument("--output", "-o", help="Output directory for exported data")
    args = parser.parse_args()
    
    try:
        cursor_path = get_cursor_data_path()
        print(f"Cursor data path: {cursor_path}")
        
        if not cursor_path.exists():
            print(f"Cursor data directory not found: {cursor_path}")
            return
        
        export_dir = create_export_directory(args.output)
        print(f"Exporting data to: {export_dir}")
        
        export_chat_sessions(cursor_path, export_dir)
        export_history(cursor_path, export_dir)
        export_copilot_chat(cursor_path, export_dir)
        export_global_storage(cursor_path, export_dir)
        
        create_summary(export_dir)
        
        print(f"\nExport completed successfully. Data saved to: {export_dir}")
        print("\nTo analyze the exported data, run:")
        print(f"  python analyze_cursor_data.py \"{export_dir}\"")
        print("Or use the --analyze flag with the shell script or batch file:")
        print("  ./export_cursor_data.sh --analyze")
        print("  export_cursor_data.bat --analyze")
    except Exception as e:
        print(f"Error during export: {e}")


if __name__ == "__main__":
    main() 