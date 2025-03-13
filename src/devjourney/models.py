"""
Data models for the DevJourney application.

This module defines the core data models used throughout the application,
including conversation data, analysis results, and Notion database structures.
"""

from datetime import datetime
from enum import Enum
import json
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyUrl, BaseModel, Field
from sqlmodel import Column, Field as SQLField, JSON
from sqlmodel import Relationship, SQLModel


class ConversationSource(str, Enum):
    """Enum representing the source of a conversation."""
    CLAUDE = "claude"
    CURSOR = "cursor"


class MessageRole(str, Enum):
    """Enum representing the role of a message in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ContentType(str, Enum):
    """Enum representing the type of content in a message."""
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    FILE = "file"


class ContentBlock(BaseModel):
    """Model representing a block of content in a message."""
    type: ContentType
    content: str
    language: Optional[str] = None  # For code blocks
    meta_data: Optional[Dict[str, Any]] = None


class Message(SQLModel, table=True):
    """Model representing a message in a conversation."""
    id: Optional[int] = SQLField(primary_key=True)
    conversation_id: int = SQLField(foreign_key="conversation.id", index=True)
    role: MessageRole
    timestamp: datetime
    content_blocks: List[Dict[str, Any]] = SQLField(sa_column=Column(JSON), default=[])
    
    conversation: "Conversation" = Relationship(back_populates="messages")


class Conversation(SQLModel, table=True):
    """Model representing a conversation."""
    id: Optional[int] = SQLField(primary_key=True)
    source: ConversationSource
    source_id: str = SQLField(index=True)
    title: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    meta_data: Dict[str, Any] = SQLField(sa_column=Column(JSON), default={})
    
    messages: List[Message] = Relationship(back_populates="conversation")
    insights: List["Insight"] = Relationship(back_populates="conversation")


class InsightType(str, Enum):
    """Enum representing the type of insight extracted from a conversation."""
    PROBLEM_SOLUTION = "problem_solution"
    LEARNING = "learning"
    CODE_REFERENCE = "code_reference"
    PROJECT_REFERENCE = "project_reference"


class InsightCategory(str, Enum):
    """Enum representing the category of an insight."""
    PROGRAMMING = "programming"
    DEVOPS = "devops"
    DESIGN = "design"
    ARCHITECTURE = "architecture"
    DATABASE = "database"
    TESTING = "testing"
    OTHER = "other"


class TechnologyTag(SQLModel, table=True):
    """Model representing a technology tag."""
    id: Optional[int] = SQLField(primary_key=True)
    name: str = SQLField(index=True, unique=True)
    
    insights: List["InsightTechnologyLink"] = Relationship(back_populates="technology")


class InsightTechnologyLink(SQLModel, table=True):
    """Many-to-many relationship between insights and technologies."""
    insight_id: int = SQLField(primary_key=True, foreign_key="insight.id")
    technology_id: int = SQLField(primary_key=True, foreign_key="technologytag.id")
    
    insight: "Insight" = Relationship(back_populates="technologies")
    technology: TechnologyTag = Relationship(back_populates="insights")


class Insight(SQLModel, table=True):
    """Model representing an insight extracted from a conversation."""
    id: Optional[int] = SQLField(primary_key=True)
    conversation_id: int = SQLField(foreign_key="conversation.id", index=True)
    type: InsightType
    category: InsightCategory
    title: str
    content: str
    code_blocks: List[Dict[str, Any]] = SQLField(sa_column=Column(JSON), default=[])
    confidence_score: float = 0.0
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    notion_page_id: Optional[str] = None
    last_synced: Optional[datetime] = None
    
    conversation: Conversation = Relationship(back_populates="insights")
    technologies: List[InsightTechnologyLink] = Relationship(back_populates="insight")


class DailyLog(SQLModel, table=True):
    """Model representing a daily log entry."""
    id: Optional[int] = SQLField(primary_key=True)
    date: datetime = SQLField(index=True, unique=True)
    summary: str
    conversation_count: int = 0
    insight_count: int = 0
    problem_solution_count: int = 0
    learning_count: int = 0
    code_reference_count: int = 0
    project_reference_count: int = 0
    notion_page_id: Optional[str] = None
    last_synced: Optional[datetime] = None


class NotionDatabaseSchema(BaseModel):
    """Model representing a Notion database schema."""
    database_id: str
    name: str
    description: Optional[str] = None
    properties: Dict[str, Dict[str, Any]]


class SyncStatus(SQLModel, table=True):
    """Model representing the sync status."""
    component: str = SQLField(primary_key=True)
    status: str = "never_run"
    last_run: Optional[datetime] = None
    details: Optional[str] = None


class NotionSyncRecord(SQLModel, table=True):
    """Model representing a record of a Notion sync."""
    insight_id: int = SQLField(primary_key=True, foreign_key="insight.id")
    notion_page_id: str
    last_synced: datetime = Field(default_factory=datetime.utcnow)


class AppConfig(SQLModel, table=True):
    """Model representing the application configuration."""
    id: Optional[int] = SQLField(primary_key=True)
    notion_api_key: Optional[str] = None
    notion_daily_log_db_id: Optional[str] = None
    notion_problem_solution_db_id: Optional[str] = None
    notion_knowledge_base_db_id: Optional[str] = None
    notion_project_tracking_db_id: Optional[str] = None
    claude_api_key: Optional[str] = None
    mcp_host: str = "localhost"
    mcp_port: int = 8000
    log_level: str = "INFO"
    data_dir: str = "./data"
    sync_interval: int = 3600
    sync_days: int = 7
    sync_batch_size: int = 50
    claude_history_path: Optional[str] = None
    cursor_history_path: Optional[str] = None
    min_confidence_threshold: float = 0.7
    analysis_batch_size: int = 100
    enable_reprocessing: bool = True
    reprocessing_days: int = 30
    reprocessing_batch_size: int = 20
    enable_advanced_analysis: bool = True
    enable_system_tray: bool = True
    enable_notifications: bool = True
    last_updated: datetime = Field(default_factory=datetime.utcnow)
