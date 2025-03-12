"""
Data models for representing conversations from various sources.
"""
from datetime import datetime
from typing import List, Dict, Optional, Union, Any
from enum import Enum
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Enum for message roles in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageContent(BaseModel):
    """Model for message content, which can be text or code."""
    text: str = Field(..., description="The text content of the message")
    language: Optional[str] = Field(None, description="Programming language if code block")
    is_code: bool = Field(False, description="Whether this content is a code block")


class Message(BaseModel):
    """Model for a message in a conversation."""
    id: str = Field(..., description="Unique identifier for the message")
    role: MessageRole = Field(..., description="Role of the message sender")
    content: List[MessageContent] = Field(..., description="Content of the message")
    timestamp: datetime = Field(..., description="Timestamp of the message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ConversationSource(str, Enum):
    """Enum for conversation sources."""
    CLAUDE = "claude"
    CURSOR = "cursor"
    MANUAL = "manual"


class Conversation(BaseModel):
    """Model for a conversation."""
    id: str = Field(..., description="Unique identifier for the conversation")
    title: Optional[str] = Field(None, description="Title of the conversation")
    source: ConversationSource = Field(..., description="Source of the conversation")
    messages: List[Message] = Field(..., description="Messages in the conversation")
    start_time: datetime = Field(..., description="Start time of the conversation")
    end_time: Optional[datetime] = Field(None, description="End time of the conversation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @property
    def duration(self) -> Optional[float]:
        """Get the duration of the conversation in seconds."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def message_count(self) -> int:
        """Get the number of messages in the conversation."""
        return len(self.messages)
    
    @property
    def user_message_count(self) -> int:
        """Get the number of user messages in the conversation."""
        return sum(1 for message in self.messages if message.role == MessageRole.USER)
    
    @property
    def assistant_message_count(self) -> int:
        """Get the number of assistant messages in the conversation."""
        return sum(1 for message in self.messages if message.role == MessageRole.ASSISTANT)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the conversation to a dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        """Create a conversation from a dictionary."""
        return cls(**data) 