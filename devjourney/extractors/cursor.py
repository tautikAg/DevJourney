"""
Extractor for Cursor chat history.
"""
import os
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from devjourney.config.settings import config
from devjourney.extractors.base import BaseExtractor
from devjourney.models.conversation import (
    Conversation, Message, MessageContent, MessageRole, ConversationSource
)

logger = logging.getLogger(__name__)


class CursorExtractor(BaseExtractor):
    """Extractor for Cursor chat history."""
    
    def __init__(self, chat_path: Optional[Path] = None, max_history_days: int = 30):
        """
        Initialize the Cursor extractor.
        
        Args:
            chat_path: Path to Cursor chat history directory
            max_history_days: Maximum number of days to extract history for
        """
        super().__init__(max_history_days)
        self.chat_path = chat_path or config.extractors.cursor_chat_path
        self.logger.info(f"Initialized Cursor extractor with chat path: {self.chat_path}")
    
    def is_available(self) -> bool:
        """
        Check if Cursor chat history is available.
        
        Returns:
            True if Cursor chat history is available, False otherwise
        """
        return self.chat_path.exists() and self.chat_path.is_dir()
    
    def extract(self, since: Optional[datetime] = None) -> List[Conversation]:
        """
        Extract conversations from Cursor chat history.
        
        Args:
            since: Only extract conversations since this datetime
            
        Returns:
            List of extracted conversations
        """
        if not self.is_available():
            self.logger.warning(f"Cursor chat history not available at {self.chat_path}")
            return []
        
        since = since or self.get_default_since_date()
        self.logger.info(f"Extracting Cursor conversations since {since.isoformat()}")
        
        conversations = []
        
        # Find all chat history files
        chat_files = list(self.chat_path.glob("*.json"))
        self.logger.info(f"Found {len(chat_files)} chat history files")
        
        for chat_file in chat_files:
            try:
                file_conversations = self._parse_chat_file(chat_file, since)
                conversations.extend(file_conversations)
            except Exception as e:
                self.logger.error(f"Error parsing chat file {chat_file}: {str(e)}")
        
        self._log_extraction_stats(conversations)
        return conversations
    
    def _parse_chat_file(self, file_path: Path, since: datetime) -> List[Conversation]:
        """
        Parse a Cursor chat history file.
        
        Args:
            file_path: Path to the chat history file
            since: Only extract conversations since this datetime
            
        Returns:
            List of conversations extracted from the file
        """
        self.logger.debug(f"Parsing chat file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                chat_data = json.load(f)
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in chat file: {file_path}")
            return []
        except Exception as e:
            self.logger.error(f"Error reading chat file {file_path}: {str(e)}")
            return []
        
        # Extract file metadata
        file_name = file_path.stem
        file_created = datetime.fromtimestamp(file_path.stat().st_ctime)
        
        # Check if the file is too old
        if file_created < since:
            self.logger.debug(f"Skipping file {file_path} (created {file_created.isoformat()})")
            return []
        
        # Parse conversations from the chat data
        conversations = []
        
        # The structure of Cursor chat files may vary, so we need to handle different formats
        if isinstance(chat_data, dict) and "conversations" in chat_data:
            # Format: {"conversations": [...]}
            raw_conversations = chat_data.get("conversations", [])
        elif isinstance(chat_data, dict) and "messages" in chat_data:
            # Format: {"messages": [...]}
            # This is a single conversation
            raw_conversations = [chat_data]
        elif isinstance(chat_data, list):
            # Format: [conversation1, conversation2, ...]
            raw_conversations = chat_data
        else:
            self.logger.warning(f"Unknown chat file format in {file_path}")
            return []
        
        for raw_conv in raw_conversations:
            try:
                conversation = self._parse_conversation(raw_conv, file_name, file_created)
                if conversation and (conversation.end_time or conversation.start_time) >= since:
                    conversations.append(conversation)
            except Exception as e:
                self.logger.error(f"Error parsing conversation in {file_path}: {str(e)}")
        
        return conversations
    
    def _parse_conversation(
        self, raw_conv: Dict[str, Any], file_name: str, file_created: datetime
    ) -> Optional[Conversation]:
        """
        Parse a single conversation from raw data.
        
        Args:
            raw_conv: Raw conversation data
            file_name: Name of the source file
            file_created: Creation time of the source file
            
        Returns:
            Parsed conversation or None if parsing failed
        """
        # Extract messages
        raw_messages = raw_conv.get("messages", [])
        if not raw_messages:
            return None
        
        # Parse messages
        messages = []
        for raw_msg in raw_messages:
            message = self._parse_message(raw_msg)
            if message:
                messages.append(message)
        
        if not messages:
            return None
        
        # Determine conversation timestamps
        start_time = min(msg.timestamp for msg in messages)
        end_time = max(msg.timestamp for msg in messages)
        
        # Generate a title from the first user message
        title = None
        for msg in messages:
            if msg.role == MessageRole.USER:
                # Extract the first line of the first content block
                if msg.content:
                    first_line = msg.content[0].text.split('\n')[0]
                    title = first_line[:50] + ('...' if len(first_line) > 50 else '')
                    break
        
        if not title:
            title = f"Cursor conversation {file_name}"
        
        # Create the conversation
        return Conversation(
            id=str(uuid.uuid4()),
            title=title,
            source=ConversationSource.CURSOR,
            messages=messages,
            start_time=start_time,
            end_time=end_time,
            metadata={
                "file_name": file_name,
                "file_created": file_created.isoformat(),
            }
        )
    
    def _parse_message(self, raw_msg: Dict[str, Any]) -> Optional[Message]:
        """
        Parse a single message from raw data.
        
        Args:
            raw_msg: Raw message data
            
        Returns:
            Parsed message or None if parsing failed
        """
        # Extract message role
        role_str = raw_msg.get("role", "").lower()
        if role_str == "user":
            role = MessageRole.USER
        elif role_str in ("assistant", "ai", "bot"):
            role = MessageRole.ASSISTANT
        elif role_str == "system":
            role = MessageRole.SYSTEM
        else:
            self.logger.warning(f"Unknown message role: {role_str}")
            return None
        
        # Extract message content
        content_str = raw_msg.get("content", "")
        if not content_str:
            return None
        
        # Parse timestamp
        timestamp_str = raw_msg.get("timestamp", "")
        try:
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                # Use created_at if available, otherwise current time
                created_at = raw_msg.get("created_at")
                if created_at:
                    timestamp = datetime.fromtimestamp(created_at)
                else:
                    timestamp = datetime.now()
        except (ValueError, TypeError):
            timestamp = datetime.now()
        
        # Parse content blocks (text and code)
        content_blocks = self._parse_content_blocks(content_str)
        
        return Message(
            id=raw_msg.get("id", str(uuid.uuid4())),
            role=role,
            content=content_blocks,
            timestamp=timestamp,
            metadata={k: v for k, v in raw_msg.items() if k not in ("id", "role", "content", "timestamp")}
        )
    
    def _parse_content_blocks(self, content_str: str) -> List[MessageContent]:
        """
        Parse content blocks from a message string.
        
        Args:
            content_str: Raw message content string
            
        Returns:
            List of parsed content blocks
        """
        blocks = []
        
        # Simple code block detection (```language ... ```)
        parts = content_str.split("```")
        
        if len(parts) == 1:
            # No code blocks
            blocks.append(MessageContent(text=content_str, is_code=False))
        else:
            for i, part in enumerate(parts):
                if i % 2 == 0:
                    # Text part
                    if part.strip():
                        blocks.append(MessageContent(text=part, is_code=False))
                else:
                    # Code part
                    # Check if the first line contains a language identifier
                    lines = part.split("\n", 1)
                    if len(lines) > 1 and lines[0].strip():
                        language = lines[0].strip()
                        code = lines[1]
                    else:
                        language = None
                        code = part
                    
                    blocks.append(MessageContent(
                        text=code,
                        language=language,
                        is_code=True
                    ))
        
        return blocks 