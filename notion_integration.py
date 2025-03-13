#!/usr/bin/env python3
"""
Notion Integration for Cursor Chat History

This script takes the extracted Cursor chat history and sends it to Notion.
It creates or updates a daily entry in your Notion database with your development activities.
"""

import os
import json
import argparse
from datetime import datetime
from pathlib import Path

try:
    from notion_client import Client
    from dotenv import load_dotenv
except ImportError:
    print("Required packages not found. Installing...")
    import subprocess
    subprocess.check_call(["pip", "install", "notion-client", "python-dotenv"])
    from notion_client import Client
    from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# Get Notion API key and database ID from environment variables
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")


def connect_to_notion():
    """Connect to the Notion API."""
    if not NOTION_API_KEY:
        raise ValueError("NOTION_API_KEY environment variable not set. Please set it in a .env file.")
    
    return Client(auth=NOTION_API_KEY)


def get_or_create_daily_page(notion, date_str):
    """Get or create a daily page in the Notion database."""
    if not NOTION_DATABASE_ID:
        raise ValueError("NOTION_DATABASE_ID environment variable not set. Please set it in a .env file.")
    
    # Check if a page for today already exists
    filter_params = {
        "filter": {
            "property": "Date",
            "date": {
                "equals": date_str
            }
        }
    }
    
    results = notion.databases.query(database_id=NOTION_DATABASE_ID, **filter_params).get("results", [])
    
    if results:
        # Page exists, return its ID
        return results[0]["id"]
    else:
        # Create a new page
        new_page = notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Date": {
                    "date": {
                        "start": date_str
                    }
                },
                "Title": {
                    "title": [
                        {
                            "text": {
                                "content": f"Development Log - {date_str}"
                            }
                        }
                    ]
                }
            }
        )
        
        return new_page["id"]


def format_chat_sessions_for_notion(chat_sessions):
    """Format chat sessions data for Notion."""
    if not chat_sessions:
        return []
    
    blocks = []
    
    # Add a heading
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": "Chat Sessions"
                    }
                }
            ]
        }
    })
    
    # Add each chat session
    for session in chat_sessions:
        # Add session heading
        blocks.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"Session: {session.get('session_id', 'Unknown')}"
                        }
                    }
                ]
            }
        })
        
        # Add files used
        if session.get("files"):
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Files: "
                            },
                            "annotations": {
                                "bold": True
                            }
                        },
                        {
                            "type": "text",
                            "text": {
                                "content": ", ".join(file.split("/")[-1] for file in session.get("files", []))
                            }
                        }
                    ]
                }
            })
        
        # Add conversations
        if session.get("conversations"):
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Conversations:"
                            },
                            "annotations": {
                                "bold": True
                            }
                        }
                    ]
                }
            })
            
            for conv in session.get("conversations", []):
                if "role" in conv and "content" in conv:
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": f"{conv['role'].capitalize()}: "
                                    },
                                    "annotations": {
                                        "bold": True,
                                        "color": "blue" if conv['role'] == "user" else "green"
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": {
                                        "content": conv["content"]
                                    }
                                }
                            ]
                        }
                    })
                elif "requestId" in conv:
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": f"Request: {conv['requestId']} (Entries: {conv.get('entries_count', 0)})"
                                    }
                                }
                            ]
                        }
                    })
        
        # Add a divider
        blocks.append({
            "object": "block",
            "type": "divider",
            "divider": {}
        })
    
    return blocks


def format_edited_files_for_notion(edited_files):
    """Format edited files data for Notion."""
    if not edited_files:
        return []
    
    blocks = []
    
    # Add a heading
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": "Edited Files"
                    }
                }
            ]
        }
    })
    
    # Add a bulleted list of files
    for file in edited_files:
        # Extract the file name from the path
        file_name = file.split("/")[-1] if "/" in file else file
        
        blocks.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": file_name
                        }
                    }
                ]
            }
        })
    
    # Add a divider
    blocks.append({
        "object": "block",
        "type": "divider",
        "divider": {}
    })
    
    return blocks


def format_code_snippets_for_notion(code_snippets):
    """Format code snippets data for Notion."""
    if not code_snippets:
        return []
    
    blocks = []
    
    # Add a heading
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": "Code Snippets"
                    }
                }
            ]
        }
    })
    
    # Add each code snippet
    for snippet in code_snippets:
        # Add file name
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"File: {snippet.get('file', '').split('/')[-1]}"
                        },
                        "annotations": {
                            "bold": True
                        }
                    }
                ]
            }
        })
        
        # Add code block
        blocks.append({
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": snippet.get("snippet", "")
                        }
                    }
                ],
                "language": snippet.get("language", "plain text")
            }
        })
        
        # Add a divider
        blocks.append({
            "object": "block",
            "type": "divider",
            "divider": {}
        })
    
    return blocks


def update_notion_page(notion, page_id, notion_data):
    """Update a Notion page with the extracted data."""
    # Format the data for Notion
    blocks = []
    
    # Add a heading
    blocks.append({
        "object": "block",
        "type": "heading_1",
        "heading_1": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": f"Development Activity - {notion_data['date']}"
                    }
                }
            ]
        }
    })
    
    # Add summary
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": f"Summary: {len(notion_data['chat_sessions'])} chat sessions, {len(notion_data['edited_files'])} edited files, {len(notion_data['code_snippets'])} code snippets"
                    }
                }
            ]
        }
    })
    
    # Add a divider
    blocks.append({
        "object": "block",
        "type": "divider",
        "divider": {}
    })
    
    # Add chat sessions
    blocks.extend(format_chat_sessions_for_notion(notion_data["chat_sessions"]))
    
    # Add edited files
    blocks.extend(format_edited_files_for_notion(notion_data["edited_files"]))
    
    # Add code snippets
    blocks.extend(format_code_snippets_for_notion(notion_data["code_snippets"]))
    
    # Update the page
    notion.blocks.children.append(page_id, children=blocks)
    
    return page_id


def main():
    parser = argparse.ArgumentParser(description="Send Cursor chat history to Notion")
    parser.add_argument("--input", "-i", required=True, help="Input JSON file with Notion data")
    args = parser.parse_args()
    
    try:
        # Load the Notion data
        input_file = Path(args.input)
        if not input_file.exists():
            raise ValueError(f"Input file not found: {input_file}")
        
        with open(input_file, 'r') as f:
            notion_data = json.load(f)
        
        # Connect to Notion
        notion = connect_to_notion()
        
        # Get or create a daily page
        date_str = notion_data["date"]
        page_id = get_or_create_daily_page(notion, date_str)
        
        # Update the page with the extracted data
        update_notion_page(notion, page_id, notion_data)
        
        print(f"Successfully updated Notion page for {date_str}")
        print(f"Page ID: {page_id}")
        
    except Exception as e:
        print(f"Error sending data to Notion: {e}")


if __name__ == "__main__":
    main() 