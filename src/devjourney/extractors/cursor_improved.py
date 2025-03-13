"""
Improved Cursor chat history extractor.

This module provides a robust implementation for extracting and monitoring
Cursor IDE chat history across different operating systems.
"""

import json
import logging
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable

import watchfiles

from devjourney.database import get_db
from devjourney.models import (
    ContentBlock,
    ContentType,
    Conversation,
    ConversationSource,
    Message,
    MessageRole,
    SyncStatus,
)

logger = logging.getLogger(__name__)


class CursorExtractorError(Exception):
    """Exception raised for Cursor extractor errors."""
    pass


class CursorExtractor:
    """Enhanced extractor for Cursor chat history with robust monitoring capabilities."""

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
            self.history_path = Path(os.path.expanduser(self.config.cursor_history_path))
        else:
            # Default paths for different platforms
            if os.name == "nt":  # Windows
                self.history_path = Path(os.environ["APPDATA"]) / "Cursor" / "chat_history"
            elif os.name == "posix":  # macOS/Linux
                # Check multiple possible locations
                possible_paths = [
                    Path.home() / ".cursor" / "chat_history",
                    Path.home() / "Library" / "Application Support" / "Cursor" / "chat_history",
                    Path.home() / ".config" / "Cursor" / "chat_history",
                ]
                
                for path in possible_paths:
                    if path.exists():
                        self.history_path = path
                        break
                else:
                    # If no path exists, use the first one but create it
                    self.history_path = possible_paths[0]
                    logger.warning(f"Cursor chat history path not found. Will create: {self.history_path}")
                    self.history_path.parent.mkdir(parents=True, exist_ok=True)
                    self.history_path.mkdir(exist_ok=True)
            else:
                raise CursorExtractorError(f"Unsupported platform: {os.name}")
        
        # Ensure the history path exists or create it
        if not self.history_path.exists():
            logger.warning(f"Creating Cursor chat history directory: {self.history_path}")
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            self.history_path.mkdir(exist_ok=True)
        
        logger.info(f"Using Cursor chat history path: {self.history_path}")
        
        # Keep track of processed files to avoid duplicates
        self.processed_files: Set[str] = set()
        
        # Initialize file patterns for different types of log files
        self.file_patterns = {
            "json": re.compile(r".*\.json$"),
            "sqlite": re.compile(r".*\.(sqlite|db)$"),
            "log": re.compile(r".*\.log$"),
        }

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
            # If it's a directory, find all relevant files
            all_files = []
            
            # Find JSON files
            json_files = list(self.history_path.glob("**/*.json"))
            all_files.extend(json_files)
            
            # Find SQLite files
            sqlite_files = list(self.history_path.glob("**/*.sqlite"))
            sqlite_files.extend(self.history_path.glob("**/*.db"))
            all_files.extend(sqlite_files)
            
            # Find log files
            log_files = list(self.history_path.glob("**/*.log"))
            all_files.extend(log_files)
            
            # Sort by modification time (newest first)
            all_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            return all_files
        else:
            logger.warning(f"Invalid Cursor chat history path: {self.history_path}")
            return []

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
            
            conversations = []
            
            # Check if the data is a list of conversations or a single conversation
            if isinstance(data, list):
                for conv_data in data:
                    if self._is_valid_conversation(conv_data):
                        conversations.append(self._normalize_conversation(conv_data, file_path))
            elif isinstance(data, dict):
                # Check if it's a conversation
                if self._is_valid_conversation(data):
                    conversations.append(self._normalize_conversation(data, file_path))
                # Check if it's a collection of conversations
                elif "conversations" in data and isinstance(data["conversations"], list):
                    for conv_data in data["conversations"]:
                        if self._is_valid_conversation(conv_data):
                            conversations.append(self._normalize_conversation(conv_data, file_path))
                # Check if it's a collection of conversations with a different structure
                elif any(key for key in data.keys() if isinstance(data[key], dict) and self._is_valid_conversation(data[key])):
                    for key, conv_data in data.items():
                        if isinstance(conv_data, dict) and self._is_valid_conversation(conv_data):
                            normalized = self._normalize_conversation(conv_data, file_path)
                            normalized["id"] = key if "id" not in conv_data else conv_data["id"]
                            conversations.append(normalized)
            
            return conversations
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in file {file_path}")
            return []
        except Exception as e:
            logger.error(f"Failed to extract chat history from JSON file {file_path}: {e}")
            return []

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
                    try:
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
                                            "messages": messages,
                                            "source_file": str(file_path)
                                        }
                                        
                                        conversations.append(normalized_conv)
                                        break  # Found messages for this conversation
                                except sqlite3.Error:
                                    # This message table might not have a conversation_id column
                                    continue
                    except sqlite3.Error as e:
                        logger.warning(f"Error querying table {conv_table}: {e}")
            
            conn.close()
            return conversations
        except sqlite3.Error as e:
            logger.warning(f"SQLite error for file {file_path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to extract chat history from SQLite file {file_path}: {e}")
            return []

    def _extract_from_log(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract chat history from a log file.
        
        Args:
            file_path: Path to the log file.
            
        Returns:
            A list of conversations.
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            
            # Try to find JSON objects in the log file
            conversations = []
            
            # Look for JSON objects enclosed in curly braces
            json_pattern = re.compile(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})')
            matches = json_pattern.findall(content)
            
            for match in matches:
                try:
                    data = json.loads(match)
                    if self._is_valid_conversation(data):
                        conversations.append(self._normalize_conversation(data, file_path))
                except json.JSONDecodeError:
                    # Not a valid JSON object, skip
                    continue
            
            return conversations
        except Exception as e:
            logger.error(f"Failed to extract chat history from log file {file_path}: {e}")
            return []

    def _is_valid_conversation(self, data: Dict[str, Any]) -> bool:
        """Check if the data represents a valid conversation.
        
        Args:
            data: The conversation data.
            
        Returns:
            True if the data represents a valid conversation, False otherwise.
        """
        if not isinstance(data, dict):
            return False
        
        # Check for required fields or patterns that indicate a conversation
        has_id = "id" in data
        has_messages = "messages" in data and isinstance(data["messages"], (list, dict))
        has_chat_structure = ("user" in data and "assistant" in data) or ("human" in data and "ai" in data)
        
        return (has_id and has_messages) or has_chat_structure

    def _normalize_conversation(self, data: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """Normalize a conversation to a standard format.
        
        Args:
            data: The conversation data.
            file_path: The file path where the conversation was found.
            
        Returns:
            A normalized conversation.
        """
        # Extract the conversation ID
        conv_id = str(data.get("id", f"cursor_{int(time.time())}_{hash(str(data))}"))
        
        # Extract the title
        title = data.get("title", "Untitled Conversation")
        
        # Extract timestamps
        start_time = self._get_timestamp(data.get("created_at") or data.get("timestamp") or data.get("start_time"))
        end_time = self._get_timestamp(data.get("updated_at") or data.get("last_message_timestamp") or data.get("end_time"))
        
        # Extract messages
        messages = []
        
        # Handle different message formats
        if "messages" in data and isinstance(data["messages"], list):
            for msg_data in data["messages"]:
                if isinstance(msg_data, dict):
                    messages.append(self._normalize_message(msg_data))
        elif "messages" in data and isinstance(data["messages"], dict):
            # Handle message dict format
            for msg_id, msg_data in data["messages"].items():
                if isinstance(msg_data, dict):
                    msg_data["id"] = msg_id
                    messages.append(self._normalize_message(msg_data))
        elif "user" in data and "assistant" in data:
            # Handle simple user/assistant format
            if isinstance(data["user"], str):
                messages.append(self._normalize_message({
                    "role": "user",
                    "content": data["user"],
                    "timestamp": start_time
                }))
            if isinstance(data["assistant"], str):
                messages.append(self._normalize_message({
                    "role": "assistant",
                    "content": data["assistant"],
                    "timestamp": end_time or self._get_timestamp(None)
                }))
        elif "human" in data and "ai" in data:
            # Handle human/ai format
            if isinstance(data["human"], str):
                messages.append(self._normalize_message({
                    "role": "user",
                    "content": data["human"],
                    "timestamp": start_time
                }))
            if isinstance(data["ai"], str):
                messages.append(self._normalize_message({
                    "role": "assistant",
                    "content": data["ai"],
                    "timestamp": end_time or self._get_timestamp(None)
                }))
        
        # Sort messages by timestamp
        messages.sort(key=lambda m: m.get("timestamp", ""))
        
        # Create a normalized conversation
        return {
            "id": conv_id,
            "title": title,
            "start_time": start_time,
            "end_time": end_time or self._get_timestamp(None),
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
        # Extract the role
        role_str = data.get("role", "user").lower()
        if role_str in ["user", "human"]:
            role = "user"
        elif role_str in ["assistant", "ai", "bot"]:
            role = "assistant"
        else:
            role = "system"
        
        # Extract the timestamp
        timestamp = self._get_timestamp(data.get("timestamp") or data.get("created_at"))
        
        # Extract the content
        content_blocks = []
        
        # Handle different content formats
        if "content" in data:
            if isinstance(data["content"], str):
                # Simple text content
                content_blocks.append({
                    "type": "text",
                    "content": data["content"],
                    "language": None,
                    "metadata": {}
                })
            elif isinstance(data["content"], list):
                # Content blocks
                for block in data["content"]:
                    if isinstance(block, dict):
                        block_type_str = block.get("type", "text").lower()
                        block_type = "text"
                        
                        if block_type_str == "code":
                            block_type = "code"
                        elif block_type_str == "image":
                            block_type = "image"
                        elif block_type_str == "file":
                            block_type = "file"
                        
                        content_blocks.append({
                            "type": block_type,
                            "content": block.get("content", ""),
                            "language": block.get("language") if block_type == "code" else None,
                            "metadata": block.get("metadata", {})
                        })
        elif "text" in data:
            # Simple text content
            content_blocks.append({
                "type": "text",
                "content": data["text"],
                "language": None,
                "metadata": {}
            })
        elif "message" in data:
            # Simple text content
            content_blocks.append({
                "type": "text",
                "content": data["message"],
                "language": None,
                "metadata": {}
            })
        
        # If no content blocks were found, add an empty one
        if not content_blocks:
            content_blocks.append({
                "type": "text",
                "content": "",
                "language": None,
                "metadata": {}
            })
        
        return {
            "role": role,
            "timestamp": timestamp,
            "content": content_blocks
        }

    def _get_timestamp(self, timestamp: Any) -> str:
        """Convert a timestamp to ISO format.
        
        Args:
            timestamp: The timestamp to convert.
            
        Returns:
            The timestamp in ISO format.
        """
        if timestamp is None:
            # Use current time
            return datetime.utcnow().isoformat()
        
        if isinstance(timestamp, (int, float)):
            # Unix timestamp
            if timestamp > 1e12:  # Milliseconds
                timestamp = timestamp / 1000
            return datetime.fromtimestamp(timestamp).isoformat()
        
        if isinstance(timestamp, str):
            try:
                # Try to parse as ISO format
                return datetime.fromisoformat(timestamp).isoformat()
            except ValueError:
                try:
                    # Try to parse as RFC 3339 format
                    timestamp = timestamp.replace("Z", "+00:00")
                    return datetime.fromisoformat(timestamp).isoformat()
                except ValueError:
                    # Use current time
                    return datetime.utcnow().isoformat()
        
        # Use current time
        return datetime.utcnow().isoformat()

    def extract_conversations(self, days: Optional[int] = None) -> List[Conversation]:
        """Extract conversations from Cursor chat history and store in the database.
        
        Args:
            days: Only extract conversations from the last N days.
            
        Returns:
            A list of extracted Conversation objects.
        """
        try:
            # Convert days to datetime if provided
            since = None
            if days is not None:
                since = datetime.utcnow() - timedelta(days=days)
            
            # Find history files
            history_files = self._find_history_files()
            
            if not history_files:
                logger.warning(f"No Cursor chat history files found in {self.history_path}")
                return []
            
            # Extract conversations from each file
            all_conversations = []
            for file_path in history_files:
                # Skip already processed files
                if str(file_path) in self.processed_files:
                    logger.debug(f"Skipping already processed file: {file_path}")
                    continue
                
                # Extract based on file type
                conversations = []
                if self.file_patterns["json"].match(file_path.name):
                    conversations = self._extract_from_json(file_path)
                elif self.file_patterns["sqlite"].match(file_path.name):
                    conversations = self._extract_from_sqlite(file_path)
                elif self.file_patterns["log"].match(file_path.name):
                    conversations = self._extract_from_log(file_path)
                else:
                    logger.debug(f"Skipping unsupported file type: {file_path}")
                    continue
                
                # Mark file as processed
                self.processed_files.add(str(file_path))
                
                all_conversations.extend(conversations)
            
            # Filter by time if needed
            if since:
                filtered_conversations = []
                for conv in all_conversations:
                    try:
                        start_time = datetime.fromisoformat(conv["start_time"])
                        if start_time >= since:
                            filtered_conversations.append(conv)
                    except (ValueError, TypeError):
                        # Skip conversations with invalid timestamps
                        continue
                all_conversations = filtered_conversations
            
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
                try:
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
                        
                        if role_str in ["user", "human"]:
                            role = MessageRole.USER
                        elif role_str in ["assistant", "ai", "bot"]:
                            role = MessageRole.ASSISTANT
                        else:
                            role = MessageRole.SYSTEM
                        
                        try:
                            timestamp = datetime.fromisoformat(msg_data["timestamp"])
                        except (ValueError, KeyError):
                            timestamp = datetime.utcnow()
                        
                        # Process content blocks
                        content_blocks = []
                        for block in msg_data.get("content", []):
                            block_type_str = block.get("type", "text").lower()
                            
                            if block_type_str == "text":
                                block_type = ContentType.TEXT
                            elif block_type_str == "code":
                                block_type = ContentType.CODE
                            elif block_type_str == "image":
                                block_type = ContentType.IMAGE
                            elif block_type_str == "file":
                                block_type = ContentType.FILE
                            else:
                                block_type = ContentType.TEXT
                            
                            content_block = ContentBlock(
                                type=block_type,
                                content=block.get("content", ""),
                                language=block.get("language") if block_type == ContentType.CODE else None,
                                metadata=block.get("metadata", {})
                            )
                            
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
                except Exception as e:
                    logger.warning(f"Failed to process conversation {conv_data.get('id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Extracted {len(processed_conversations)} conversations from Cursor")
            
            # Update sync status
            sync_status = SyncStatus(
                component="extraction",
                status="completed",
                last_run=datetime.utcnow(),
                details=f"Extracted {len(processed_conversations)} conversations from Cursor"
            )
            self.db.update_or_create_item(sync_status, component="extraction")
            
            return processed_conversations
        except Exception as e:
            logger.error(f"Failed to extract conversations from Cursor: {e}")
            
            # Update sync status
            sync_status = SyncStatus(
                component="extraction",
                status="failed",
                last_run=datetime.utcnow(),
                details=f"Failed to extract conversations from Cursor: {e}"
            )
            self.db.update_or_create_item(sync_status, component="extraction")
            
            return []

    def watch_for_changes(self, callback: Callable) -> None:
        """Watch for changes in the Cursor chat history.
        
        Args:
            callback: A callback function to call when changes are detected.
                     The callback will receive a list of changes.
        """
        try:
            logger.info(f"Watching for changes in {self.history_path}")
            
            # Ensure the directory exists
            if not self.history_path.exists():
                logger.warning(f"Creating Cursor chat history directory: {self.history_path}")
                self.history_path.parent.mkdir(parents=True, exist_ok=True)
                self.history_path.mkdir(exist_ok=True)
            
            # Watch for changes in the history path
            for changes in watchfiles.watch(self.history_path, recursive=True):
                logger.info(f"Detected {len(changes)} changes in Cursor chat history")
                
                # Process changes
                changed_files = []
                for change_type, file_path in changes:
                    if change_type in [watchfiles.Change.added, watchfiles.Change.modified]:
                        changed_files.append(file_path)
                
                # Call the callback function with the changes
                if changed_files:
                    callback(changed_files)
        except Exception as e:
            logger.error(f"Failed to watch for changes in Cursor chat history: {e}")
            
            # Try to recover by restarting the watch after a delay
            logger.info("Attempting to restart watch after 10 seconds...")
            time.sleep(10)
            self.watch_for_changes(callback)


def get_cursor_extractor() -> CursorExtractor:
    """Get a Cursor extractor.
    
    Returns:
        A Cursor extractor.
    """
    try:
        return CursorExtractor()
    except CursorExtractorError as e:
        logger.warning(f"Failed to initialize Cursor extractor: {e}")
        
        # Create a directory for Cursor chat history
        history_path = Path.home() / ".cursor" / "chat_history"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.mkdir(exist_ok=True)
        
        logger.info(f"Created Cursor chat history directory: {history_path}")
        return CursorExtractor(str(history_path)) 