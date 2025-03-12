"""
Data models for representing Notion database structure and content.
"""
from datetime import datetime
from typing import List, Dict, Optional, Union, Any
from enum import Enum
from pydantic import BaseModel, Field


class NotionPropertyType(str, Enum):
    """Enum for Notion property types."""
    TITLE = "title"
    RICH_TEXT = "rich_text"
    NUMBER = "number"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    DATE = "date"
    PEOPLE = "people"
    FILES = "files"
    CHECKBOX = "checkbox"
    URL = "url"
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    FORMULA = "formula"
    RELATION = "relation"
    ROLLUP = "rollup"
    CREATED_TIME = "created_time"
    CREATED_BY = "created_by"
    LAST_EDITED_TIME = "last_edited_time"
    LAST_EDITED_BY = "last_edited_by"


class NotionProperty(BaseModel):
    """Model for a Notion property."""
    name: str = Field(..., description="Name of the property")
    type: NotionPropertyType = Field(..., description="Type of the property")
    options: Optional[List[Dict[str, Any]]] = Field(None, description="Options for select/multi-select")
    formula: Optional[Dict[str, Any]] = Field(None, description="Formula for formula property")
    relation: Optional[Dict[str, Any]] = Field(None, description="Relation configuration")
    rollup: Optional[Dict[str, Any]] = Field(None, description="Rollup configuration")


class NotionDatabaseSchema(BaseModel):
    """Model for a Notion database schema."""
    id: Optional[str] = Field(None, description="ID of the database")
    title: str = Field(..., description="Title of the database")
    description: Optional[str] = Field(None, description="Description of the database")
    properties: Dict[str, NotionProperty] = Field(..., description="Properties of the database")
    
    def to_notion_format(self) -> Dict[str, Any]:
        """Convert the schema to Notion API format."""
        result = {
            "title": [{"type": "text", "text": {"content": self.title}}],
            "properties": {}
        }
        
        if self.description:
            result["description"] = [{"type": "text", "text": {"content": self.description}}]
        
        for name, prop in self.properties.items():
            prop_data = {"type": prop.type}
            
            if prop.type in (NotionPropertyType.SELECT, NotionPropertyType.MULTI_SELECT) and prop.options:
                prop_data[prop.type] = {"options": prop.options}
            elif prop.type == NotionPropertyType.FORMULA and prop.formula:
                prop_data["formula"] = prop.formula
            elif prop.type == NotionPropertyType.RELATION and prop.relation:
                prop_data["relation"] = prop.relation
            elif prop.type == NotionPropertyType.ROLLUP and prop.rollup:
                prop_data["rollup"] = prop.rollup
            
            result["properties"][name] = prop_data
        
        return result


class NotionPage(BaseModel):
    """Model for a Notion page."""
    id: Optional[str] = Field(None, description="ID of the page")
    parent_id: str = Field(..., description="ID of the parent database")
    title: str = Field(..., description="Title of the page")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Properties of the page")
    content: List[Dict[str, Any]] = Field(default_factory=list, description="Content blocks of the page")
    
    def to_notion_format(self) -> Dict[str, Any]:
        """Convert the page to Notion API format."""
        result = {
            "parent": {"database_id": self.parent_id},
            "properties": {}
        }
        
        # Add title property
        result["properties"]["Name"] = {
            "title": [{"text": {"content": self.title}}]
        }
        
        # Add other properties
        for name, value in self.properties.items():
            if name != "Name":  # Skip title as it's already added
                result["properties"][name] = value
        
        return result


# Predefined database schemas
DAILY_LOG_SCHEMA = NotionDatabaseSchema(
    title="DevJourney Daily Log",
    description="Daily summaries of your development journey",
    properties={
        "Name": NotionProperty(name="Name", type=NotionPropertyType.TITLE),
        "Date": NotionProperty(name="Date", type=NotionPropertyType.DATE),
        "Conversations": NotionProperty(name="Conversations", type=NotionPropertyType.NUMBER),
        "Problems Solved": NotionProperty(name="Problems Solved", type=NotionPropertyType.NUMBER),
        "Learnings": NotionProperty(name="Learnings", type=NotionPropertyType.NUMBER),
        "Code References": NotionProperty(name="Code References", type=NotionPropertyType.NUMBER),
        "Meetings": NotionProperty(name="Meetings", type=NotionPropertyType.NUMBER),
        "Summary": NotionProperty(name="Summary", type=NotionPropertyType.RICH_TEXT),
        "Highlights": NotionProperty(name="Highlights", type=NotionPropertyType.RICH_TEXT),
    }
)

PROBLEM_SOLUTION_SCHEMA = NotionDatabaseSchema(
    title="DevJourney Problems & Solutions",
    description="Technical problems and their solutions",
    properties={
        "Name": NotionProperty(name="Name", type=NotionPropertyType.TITLE),
        "Date": NotionProperty(name="Date", type=NotionPropertyType.DATE),
        "Problem": NotionProperty(name="Problem", type=NotionPropertyType.RICH_TEXT),
        "Solution": NotionProperty(name="Solution", type=NotionPropertyType.RICH_TEXT),
        "Tags": NotionProperty(
            name="Tags", 
            type=NotionPropertyType.MULTI_SELECT,
            options=[
                {"name": "JavaScript", "color": "blue"},
                {"name": "Python", "color": "green"},
                {"name": "AWS", "color": "orange"},
                {"name": "React", "color": "purple"},
                {"name": "Node.js", "color": "yellow"},
                {"name": "Docker", "color": "red"},
            ]
        ),
        "Source": NotionProperty(
            name="Source", 
            type=NotionPropertyType.SELECT,
            options=[
                {"name": "Claude", "color": "purple"},
                {"name": "Cursor", "color": "blue"},
                {"name": "Manual", "color": "gray"},
            ]
        ),
    }
)

LEARNING_SCHEMA = NotionDatabaseSchema(
    title="DevJourney Learnings",
    description="Concepts and knowledge gained during development",
    properties={
        "Name": NotionProperty(name="Name", type=NotionPropertyType.TITLE),
        "Date": NotionProperty(name="Date", type=NotionPropertyType.DATE),
        "Concept": NotionProperty(name="Concept", type=NotionPropertyType.RICH_TEXT),
        "Explanation": NotionProperty(name="Explanation", type=NotionPropertyType.RICH_TEXT),
        "Examples": NotionProperty(name="Examples", type=NotionPropertyType.RICH_TEXT),
        "Tags": NotionProperty(
            name="Tags", 
            type=NotionPropertyType.MULTI_SELECT,
            options=[
                {"name": "JavaScript", "color": "blue"},
                {"name": "Python", "color": "green"},
                {"name": "AWS", "color": "orange"},
                {"name": "React", "color": "purple"},
                {"name": "Node.js", "color": "yellow"},
                {"name": "Docker", "color": "red"},
            ]
        ),
        "Source": NotionProperty(
            name="Source", 
            type=NotionPropertyType.SELECT,
            options=[
                {"name": "Claude", "color": "purple"},
                {"name": "Cursor", "color": "blue"},
                {"name": "Manual", "color": "gray"},
            ]
        ),
    }
)

CODE_REFERENCE_SCHEMA = NotionDatabaseSchema(
    title="DevJourney Code References",
    description="Useful code snippets and references",
    properties={
        "Name": NotionProperty(name="Name", type=NotionPropertyType.TITLE),
        "Date": NotionProperty(name="Date", type=NotionPropertyType.DATE),
        "Language": NotionProperty(
            name="Language", 
            type=NotionPropertyType.SELECT,
            options=[
                {"name": "JavaScript", "color": "blue"},
                {"name": "Python", "color": "green"},
                {"name": "HTML", "color": "orange"},
                {"name": "CSS", "color": "purple"},
                {"name": "SQL", "color": "yellow"},
                {"name": "Bash", "color": "red"},
                {"name": "Other", "color": "gray"},
            ]
        ),
        "Code": NotionProperty(name="Code", type=NotionPropertyType.RICH_TEXT),
        "Explanation": NotionProperty(name="Explanation", type=NotionPropertyType.RICH_TEXT),
        "File Path": NotionProperty(name="File Path", type=NotionPropertyType.RICH_TEXT),
        "Tags": NotionProperty(
            name="Tags", 
            type=NotionPropertyType.MULTI_SELECT,
            options=[
                {"name": "Algorithm", "color": "blue"},
                {"name": "Utility", "color": "green"},
                {"name": "Component", "color": "orange"},
                {"name": "Configuration", "color": "purple"},
                {"name": "API", "color": "yellow"},
                {"name": "Database", "color": "red"},
            ]
        ),
        "Source": NotionProperty(
            name="Source", 
            type=NotionPropertyType.SELECT,
            options=[
                {"name": "Claude", "color": "purple"},
                {"name": "Cursor", "color": "blue"},
                {"name": "Manual", "color": "gray"},
            ]
        ),
    }
) 