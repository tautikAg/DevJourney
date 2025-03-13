"""
Cursor chat history extractor.

This module extracts chat history from the Cursor IDE and stores it in the database.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from watchfiles import watch

from devjourney.database import get_db
from devjourney.models import (
    ContentBlock,
    ContentType,
    Conversation,
    ConversationSource,
    Message,
    MessageRole,
)

logger = logging.getLogger(__name__)


class CursorExtractorError(Exception):
    """Exception raised for Cursor extractor errors."""
    pass


class CursorExtractor:
    """Extractor for Cursor chat history."""

    def __init__(self, history_path: Optional[str] = None):
        """Initialize the Cursor extractor.
        
        Args:
            history_path: Path to the Cursor chat history. If None, uses the default path.
        """
        self.db = get_db()
        self.config = self.db.get_config()
        
        # Determine the history path
        if history_path:
            self.history_path = Path(history_path)
        elif self.config.cursor_history_path:
            self.history_path = Path(self.config.cursor_history_path)
        else:
            # Default paths for different platforms
            if os.name == "nt":  # Windows
                self.history_path = Path(os.environ["APPDATA"]) / "Cursor" / "chat_history"
            elif os.name == "posix":  # macOS/Linux
                if os.path.exists(Path.home() / ".cursor"):
                    self.history_path = Path.home() / ".cursor" / "chat_history"
                elif os.path.exists(Path.home() / "Library" / "Application Support" / "Cursor"):
                    self.history_path = Path.home() / "Library" / "Application Support" / "Cursor" / "chat_history"
                else:
                    raise CursorExtractorError("Could not find Cursor chat history path")
            else:
                raise CursorExtractorError(f"Unsupported platform: {os.name}")
        
        # Ensure the history path exists
        if not self.history_path.exists():
            raise CursorExtractorError(f"Cursor chat history path does not exist: {self.history_path}")
        
        logger.info(f"Using Cursor chat history path: {self.history_path}")

    def _find_history_files(self) -> List[Path]:
        """Find Cursor chat history files.
        
        Returns:
            A list of chat history file paths.
        """
        # Check if the history path is a file or directory
        if self.history_path.is_file():
            # If it's a file, just return it
            return [self.history_path]
        elif self.history_path.is_dir():
            # If it's a directory, find all JSON and SQLite files
            json_files = list(self.history_path.glob("*.json"))
            sqlite_files = list(self.history_path.glob("*.sqlite"))
            sqlite_files.extend(self.history_path.glob("*.db"))
            
            return json_files + sqlite_files
        else:
            raise CursorExtractorError(f"Invalid Cursor chat history path: {self.history_path}")

    def _extract_from_json(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract chat history from a JSON file.
        
        Args:
            file_path: Path to the JSON file.
            
        Returns:
            A list of conversations.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # The structure of the JSON file depends on Cursor's implementation
            # This is a placeholder for the actual implementation
            conversations = []
            
            # Check if the data is a list of conversations or a single conversation
            if isinstance(data, list):
                for conv_data in data:
                    if self._is_valid_conversation(conv_data):
                        conversations.append(self._normalize_conversation(conv_data, file_path))
            elif isinstance(data, dict):
                if self._is_valid_conversation(data):
                    conversations.append(self._normalize_conversation(data, file_path))
            
            return conversations
        except Exception as e:
            logger.error(f"Failed to extract chat history from JSON file {file_path}: {e}")
            raise CursorExtractorError(f"Failed to extract chat history from JSON file {file_path}: {e}")

    def _extract_from_sqlite(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract chat history from a SQLite file.
        
        Args:
            file_path: Path to the SQLite file.
            
        Returns:
            A list of conversations.
        """
        try:
            conn = sqlite3.connect(file_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # The structure of the SQLite database depends on Cursor's implementation
            # This is a placeholder for the actual implementation
            
            # First, try to get the table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            conversations = []
            
            # Look for tables that might contain conversations
            conversation_tables = [t for t in tables if "conversation" in t.lower() or "chat" in t.lower()]
            message_tables = [t for t in tables if "message" in t.lower()]
            
            if conversation_tables and message_tables:
                # If we have both conversation and message tables, we can extract the data
                for conv_table in conversation_tables:
                    # Get all conversations
                    cursor.execute(f"SELECT * FROM {conv_table}")
                    conv_rows = cursor.fetchall()
                    
                    for conv_row in conv_rows:
                        conv_data = dict(conv_row)
                        conv_id = conv_data.get("id") or conv_data.get("conversation_id")
                        
                        if not conv_id:
                            continue
                        
                        # Get messages for this conversation
                        for msg_table in message_tables:
                            try:
                                cursor.execute(f"SELECT * FROM {msg_table} WHERE conversation_id = ? ORDER BY timestamp", (conv_id,))
                                msg_rows = cursor.fetchall()
                                
                                if msg_rows:
                                    messages = []
                                    for msg_row in msg_rows:
                                        msg_data = dict(msg_row)
                                        messages.append(self._normalize_message(msg_data))
                                    
                                    # Create a normalized conversation
                                    normalized_conv = {
                                        "id": str(conv_id),
                                        "title": conv_data.get("title", "Untitled Conversation"),
                                        "start_time": self._get_timestamp(conv_data.get("created_at") or conv_data.get("timestamp")),
                                        "end_time": self._get_timestamp(conv_data.get("updated_at") or conv_data.get("last_message_timestamp")),
                                        "messages": messages
                                    }
                                    
                                    conversations.append(normalized_conv)
                                    break  # Found messages for this conversation, no need to check other message tables
                            except sqlite3.Error:
                                # This message table might not have a conversation_id column, try the next one
                                continue
            
            conn.close()
            return conversations
        except Exception as e:
            logger.error(f"Failed to extract chat history from SQLite file {file_path}: {e}")
            raise CursorExtractorError(f"Failed to extract chat history from SQLite file {file_path}: {e}")

    def _is_valid_conversation(self, data: Dict[str, Any]) -> bool:
        """Check if the data represents a valid conversation.
        
        Args:
            data: The conversation data.
            
        Returns:
            True if the data represents a valid conversation, False otherwise.
        """
        # Check if the data has the required fields
        if not isinstance(data, dict):
            return False
        
        # Check for required fields
        has_id = "id" in data
        has_messages = "messages" in data and isinstance(data["messages"], list)
        
        return has_id and has_messages

    def _normalize_conversation(self, data: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """Normalize a conversation to a standard format.
        
        Args:
            data: The conversation data.
            file_path: The file path where the conversation was found.
            
        Returns:
            A normalized conversation.
        """
        # Extract the conversation ID
        conv_id = str(data["id"])
        
        # Extract the title
        title = data.get("title", "Untitled Conversation")
        
        # Extract timestamps
        start_time = self._get_timestamp(data.get("created_at") or data.get("timestamp") or data.get("start_time"))
        end_time = self._get_timestamp(data.get("updated_at") or data.get("last_message_timestamp") or data.get("end_time"))
        
        # Extract messages
        messages = []
        for msg_data in data.get("messages", []):
            if isinstance(msg_data, dict):
                messages.append(self._normalize_message(msg_data))
        
        # Create a normalized conversation
        return {
            "id": conv_id,
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
            "messages": messages,
            "source_file": str(file_path)
        }

    def _normalize_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a message to a standard format.
        
        Args:
            data: The message data.
            
        Returns:
            A normalized message.
        """
        # Extract the message ID
        msg_id = str(data.get("id", ""))
        
        # Extract the role
        role_str = data.get("role", "").lower()
        if role_str == "user":
            role = "user"
        elif role_str in ["assistant", "ai", "bot", "cursor"]:
            role = "assistant"
        elif role_str == "system":
            role = "system"
        else:
            # Default to user if role is unknown
            role = "user"
        
        # Extract the timestamp
        timestamp = self._get_timestamp(data.get("timestamp") or data.get("created_at"))
        
        # Extract the content
        content = []
        
        # Check if the content is a string or a list of blocks
        if "content" in data:
            if isinstance(data["content"], str):
                # Simple text content
                content.append({
                    "type": "text",
                    "content": data["content"]
                })
            elif isinstance(data["content"], list):
                # List of content blocks
                for block in data["content"]:
                    if isinstance(block, dict) and "type" in block and "content" in block:
                        content.append(block)
                    elif isinstance(block, str):
                        content.append({
                            "type": "text",
                            "content": block
                        })
        elif "text" in data:
            # Simple text content
            content.append({
                "type": "text",
                "content": data["text"]
            })
        
        # Check for code blocks
        if "code" in data and data["code"]:
            content.append({
                "type": "code",
                "content": data["code"],
                "language": data.get("language", "")
            })
        
        # Create a normalized message
        return {
            "id": msg_id,
            "role": role,
            "timestamp": timestamp,
            "content": content
        }

    def _get_timestamp(self, timestamp: Any) -> str:
        """Convert a timestamp to ISO format.
        
        Args:
            timestamp: The timestamp to convert.
            
        Returns:
            The timestamp in ISO format.
        """
        if not timestamp:
            # Use current time if no timestamp is provided
            return datetime.utcnow().isoformat()
        
        if isinstance(timestamp, (int, float)):
            # Unix timestamp (seconds or milliseconds)
            if timestamp > 1e12:  # Milliseconds
                dt = datetime.fromtimestamp(timestamp / 1000)
            else:  # Seconds
                dt = datetime.fromtimestamp(timestamp)
            return dt.isoformat()
        elif isinstance(timestamp, str):
            # Try to parse the timestamp
            try:
                dt = datetime.fromisoformat(timestamp)
                return dt.isoformat()
            except ValueError:
                # If parsing fails, use current time
                return datetime.utcnow().isoformat()
        else:
            # Unknown format, use current time
            return datetime.utcnow().isoformat()

    def extract_conversations(self, since: Optional[datetime] = None) -> List[Conversation]:
        """Extract conversations from Cursor chat history and store in the database.
        
        Args:
            since: Only extract conversations since this time.
            
        Returns:
            A list of extracted Conversation objects.
        """
        try:
            # Find history files
            history_files = self._find_history_files()
            
            if not history_files:
                logger.warning(f"No Cursor chat history files found in {self.history_path}")
                return []
            
            # Extract conversations from each file
            all_conversations = []
            for file_path in history_files:
                if file_path.suffix.lower() == ".json":
                    conversations = self._extract_from_json(file_path)
                elif file_path.suffix.lower() in [".sqlite", ".db"]:
                    conversations = self._extract_from_sqlite(file_path)
                else:
                    logger.warning(f"Unsupported file type: {file_path}")
                    continue
                
                all_conversations.extend(conversations)
            
            # Filter by time if needed
            if since:
                all_conversations = [
                    conv for conv in all_conversations 
                    if datetime.fromisoformat(conv["start_time"]) >= since
                ]
            
            # Process and store conversations
            processed_conversations = []
            for conv_data in all_conversations:
                # Check if conversation already exists in the database
                existing_convs = self.db.get_items(
                    Conversation, 
                    source=ConversationSource.CURSOR, 
                    source_id=conv_data["id"]
                )
                
                if existing_convs:
                    logger.debug(f"Conversation {conv_data['id']} already exists, skipping")
                    processed_conversations.append(existing_convs[0])
                    continue
                
                # Create a new conversation
                start_time = datetime.fromisoformat(conv_data["start_time"])
                end_time = datetime.fromisoformat(conv_data["end_time"]) if "end_time" in conv_data else None
                
                conversation = Conversation(
                    source=ConversationSource.CURSOR,
                    source_id=conv_data["id"],
                    title=conv_data.get("title", "Untitled Conversation"),
                    start_time=start_time,
                    end_time=end_time,
                    metadata={"source_file": conv_data.get("source_file", "")}
                )
                
                # Add the conversation to the database
                conversation = self.db.add_item(conversation)
                
                # Process messages
                messages = []
                for msg_data in conv_data.get("messages", []):
                    role_str = msg_data.get("role", "user").lower()
                    role = MessageRole.USER if role_str == "user" else MessageRole.ASSISTANT if role_str == "assistant" else MessageRole.SYSTEM
                    
                    timestamp = datetime.fromisoformat(msg_data["timestamp"])
                    
                    # Process content blocks
                    content_blocks = []
                    for block in msg_data.get("content", []):
                        block_type_str = block.get("type", "text").lower()
                        block_type = ContentType.TEXT
                        
                        if block_type_str == "code":
                            block_type = ContentType.CODE
                        elif block_type_str == "image":
                            block_type = ContentType.IMAGE
                        elif block_type_str == "file":
                            block_type = ContentType.FILE
                        
                        content_block = {
                            "type": block_type,
                            "content": block.get("content", ""),
                            "language": block.get("language") if block_type == ContentType.CODE else None,
                            "metadata": block.get("metadata", {})
                        }
                        
                        content_blocks.append(content_block)
                    
                    message = Message(
                        conversation_id=conversation.id,
                        role=role,
                        timestamp=timestamp,
                        content_blocks=content_blocks
                    )
                    
                    messages.append(message)
                
                # Add messages to the database
                if messages:
                    self.db.add_items(messages)
                
                processed_conversations.append(conversation)
            
            logger.info(f"Extracted {len(processed_conversations)} conversations from Cursor")
            
            return processed_conversations
        except Exception as e:
            logger.error(f"Failed to extract conversations from Cursor: {e}")
            raise CursorExtractorError(f"Failed to extract conversations from Cursor: {e}")

    def watch_for_changes(self, callback: callable) -> None:
        """Watch for changes in the Cursor chat history.
        
        Args:
            callback: A callback function to call when changes are detected.
        """
        try:
            logger.info(f"Watching for changes in {self.history_path}")
            
            # Watch for changes in the history path
            for changes in watch(self.history_path):
                logger.debug(f"Detected changes in Cursor chat history: {changes}")
                
                # Call the callback function
                callback()
        except Exception as e:
            logger.error(f"Failed to watch for changes in Cursor chat history: {e}")
            raise CursorExtractorError(f"Failed to watch for changes in Cursor chat history: {e}")


def get_cursor_extractor() -> CursorExtractor:
    """Get a Cursor extractor.
    
    Returns:
        A Cursor extractor.
    """
    db = get_db()
    config = db.get_config()
    
    extractor = CursorExtractor(
        history_path=config.cursor_history_path
    )
    
    return extractor
