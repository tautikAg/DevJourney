"""
Data models for representing analyzed content from conversations.
"""
from datetime import datetime
from typing import List, Dict, Optional, Union, Any, Set
from enum import Enum
from pydantic import BaseModel, Field, validator


class ContentCategory(str, Enum):
    """Enum for content categories."""
    PROBLEM_SOLUTION = "Problem/Solution"
    LEARNING = "Learning"
    CODE_REFERENCE = "Code Reference"
    MEETING_NOTES = "Meeting Notes"
    CUSTOM = "Custom"


class ContentItem(BaseModel):
    """Model for a content item extracted from a conversation."""
    id: str = Field(..., description="Unique identifier for the content item")
    conversation_id: str = Field(..., description="ID of the source conversation")
    category: ContentCategory = Field(..., description="Category of the content item")
    title: str = Field(..., description="Title of the content item")
    content: str = Field(..., description="Content of the item")
    timestamp: datetime = Field(..., description="Timestamp of the content item")
    tags: List[str] = Field(default_factory=list, description="Tags for the content item")
    source_message_ids: List[str] = Field(default_factory=list, description="IDs of source messages")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ProblemSolution(ContentItem):
    """Model for a problem-solution pair."""
    problem_statement: str = Field(..., description="Statement of the problem")
    solution: str = Field(..., description="Solution to the problem")
    code_snippets: List[Dict[str, str]] = Field(
        default_factory=list, 
        description="Code snippets in the solution"
    )
    
    @validator('category')
    def validate_category(cls, v):
        """Validate that the category is PROBLEM_SOLUTION."""
        if v != ContentCategory.PROBLEM_SOLUTION:
            raise ValueError(f"Category must be {ContentCategory.PROBLEM_SOLUTION}")
        return v


class Learning(ContentItem):
    """Model for a learning item."""
    concept: str = Field(..., description="The concept learned")
    explanation: str = Field(..., description="Explanation of the concept")
    examples: List[str] = Field(default_factory=list, description="Examples of the concept")
    related_concepts: List[str] = Field(default_factory=list, description="Related concepts")
    
    @validator('category')
    def validate_category(cls, v):
        """Validate that the category is LEARNING."""
        if v != ContentCategory.LEARNING:
            raise ValueError(f"Category must be {ContentCategory.LEARNING}")
        return v


class CodeReference(ContentItem):
    """Model for a code reference item."""
    language: str = Field(..., description="Programming language of the code")
    code: str = Field(..., description="The code snippet")
    explanation: str = Field(..., description="Explanation of the code")
    file_path: Optional[str] = Field(None, description="Path to the file if applicable")
    
    @validator('category')
    def validate_category(cls, v):
        """Validate that the category is CODE_REFERENCE."""
        if v != ContentCategory.CODE_REFERENCE:
            raise ValueError(f"Category must be {ContentCategory.CODE_REFERENCE}")
        return v


class MeetingNotes(ContentItem):
    """Model for meeting notes."""
    participants: List[str] = Field(default_factory=list, description="Participants in the meeting")
    action_items: List[str] = Field(default_factory=list, description="Action items from the meeting")
    decisions: List[str] = Field(default_factory=list, description="Decisions made in the meeting")
    
    @validator('category')
    def validate_category(cls, v):
        """Validate that the category is MEETING_NOTES."""
        if v != ContentCategory.MEETING_NOTES:
            raise ValueError(f"Category must be {ContentCategory.MEETING_NOTES}")
        return v


class DailySummary(BaseModel):
    """Model for a daily summary."""
    id: str = Field(..., description="Unique identifier for the summary")
    date: datetime = Field(..., description="Date of the summary")
    conversation_count: int = Field(0, description="Number of conversations")
    problem_count: int = Field(0, description="Number of problems solved")
    learning_count: int = Field(0, description="Number of learnings")
    code_reference_count: int = Field(0, description="Number of code references")
    meeting_count: int = Field(0, description="Number of meetings")
    summary_text: str = Field(..., description="Summary text")
    highlights: List[str] = Field(default_factory=list, description="Highlights of the day")
    content_items: List[str] = Field(default_factory=list, description="IDs of content items")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AnalysisResult(BaseModel):
    """Model for the result of analyzing conversations."""
    content_items: List[ContentItem] = Field(default_factory=list, description="Extracted content items")
    daily_summaries: List[DailySummary] = Field(default_factory=list, description="Daily summaries")
    tags: Set[str] = Field(default_factory=set, description="All tags found in content items")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    def add_content_item(self, item: ContentItem) -> None:
        """Add a content item to the analysis result."""
        self.content_items.append(item)
        self.tags.update(item.tags)
    
    def get_items_by_category(self, category: ContentCategory) -> List[ContentItem]:
        """Get content items by category."""
        return [item for item in self.content_items if item.category == category]
    
    def get_items_by_tag(self, tag: str) -> List[ContentItem]:
        """Get content items by tag."""
        return [item for item in self.content_items if tag in item.tags]
    
    def get_items_by_date_range(self, start_date: datetime, end_date: datetime) -> List[ContentItem]:
        """Get content items by date range."""
        return [
            item for item in self.content_items 
            if start_date <= item.timestamp <= end_date
        ] 