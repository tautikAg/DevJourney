"""
Notion database schema management for DevJourney.

This module handles the creation and management of Notion database schemas
for storing progress tracking data.
"""

import logging
from typing import Any, Dict, List, Optional

from devjourney.database import get_db
from devjourney.models import InsightCategory, NotionDatabaseSchema
from devjourney.notion.client import NotionClient, get_notion_client

logger = logging.getLogger(__name__)


class NotionDatabaseError(Exception):
    """Exception raised for Notion database errors."""
    pass


# Daily Log database schema
DAILY_LOG_SCHEMA = NotionDatabaseSchema(
    database_id="",
    name="DevJourney Daily Logs",
    description="Daily logs of your development journey",
    properties={
        "Date": {
            "date": {}
        },
        "Summary": {
            "rich_text": {}
        },
        "Conversations": {
            "number": {}
        },
        "Insights": {
            "number": {}
        },
        "Problem Solutions": {
            "number": {}
        },
        "Learnings": {
            "number": {}
        },
        "Code References": {
            "number": {}
        },
        "Project References": {
            "number": {}
        },
        "Last Synced": {
            "date": {}
        }
    }
)

# Problem Solution database schema
PROBLEM_SOLUTION_SCHEMA = NotionDatabaseSchema(
    database_id="",
    name="DevJourney Problem Solutions",
    description="Problem solutions extracted from your conversations",
    properties={
        "Title": {
            "title": {}
        },
        "Category": {
            "select": {
                "options": [
                    {"name": category.value, "color": "default"}
                    for category in InsightCategory
                ]
            }
        },
        "Technologies": {
            "multi_select": {
                "options": [
                    {"name": "Python", "color": "blue"},
                    {"name": "JavaScript", "color": "yellow"},
                    {"name": "React", "color": "blue"},
                    {"name": "Node.js", "color": "green"},
                    {"name": "SQL", "color": "orange"},
                    {"name": "Docker", "color": "blue"},
                    {"name": "AWS", "color": "orange"},
                    {"name": "Git", "color": "red"},
                ]
            }
        },
        "Confidence": {
            "number": {}
        },
        "Extracted At": {
            "date": {}
        },
        "Conversation": {
            "rich_text": {}
        },
        "Last Synced": {
            "date": {}
        }
    }
)

# Knowledge Base database schema
KNOWLEDGE_BASE_SCHEMA = NotionDatabaseSchema(
    database_id="",
    name="DevJourney Knowledge Base",
    description="Knowledge base extracted from your conversations",
    properties={
        "Title": {
            "title": {}
        },
        "Category": {
            "select": {
                "options": [
                    {"name": category.value, "color": "default"}
                    for category in InsightCategory
                ]
            }
        },
        "Type": {
            "select": {
                "options": [
                    {"name": "Learning", "color": "green"},
                    {"name": "Code Reference", "color": "blue"},
                ]
            }
        },
        "Technologies": {
            "multi_select": {
                "options": [
                    {"name": "Python", "color": "blue"},
                    {"name": "JavaScript", "color": "yellow"},
                    {"name": "React", "color": "blue"},
                    {"name": "Node.js", "color": "green"},
                    {"name": "SQL", "color": "orange"},
                    {"name": "Docker", "color": "blue"},
                    {"name": "AWS", "color": "orange"},
                    {"name": "Git", "color": "red"},
                ]
            }
        },
        "Confidence": {
            "number": {}
        },
        "Extracted At": {
            "date": {}
        },
        "Conversation": {
            "rich_text": {}
        },
        "Last Synced": {
            "date": {}
        }
    }
)

# Project Tracking database schema
PROJECT_TRACKING_SCHEMA = NotionDatabaseSchema(
    database_id="",
    name="DevJourney Project Tracking",
    description="Track your development projects",
    properties={
        "Project": {
            "title": {}
        },
        "Status": {
            "select": {
                "options": [
                    {"name": "Not Started", "color": "gray"},
                    {"name": "In Progress", "color": "blue"},
                    {"name": "Completed", "color": "green"},
                    {"name": "On Hold", "color": "yellow"},
                ]
            }
        },
        "Technologies": {
            "multi_select": {
                "options": [
                    {"name": "Python", "color": "blue"},
                    {"name": "JavaScript", "color": "yellow"},
                    {"name": "React", "color": "blue"},
                    {"name": "Node.js", "color": "green"},
                    {"name": "SQL", "color": "orange"},
                    {"name": "Docker", "color": "blue"},
                    {"name": "AWS", "color": "orange"},
                    {"name": "Git", "color": "red"},
                ]
            }
        },
        "Start Date": {
            "date": {}
        },
        "Last Updated": {
            "date": {}
        },
        "Related Insights": {
            "number": {}
        }
    }
)


class NotionDatabaseManager:
    """Manager for Notion databases."""

    def __init__(self, client: Optional[NotionClient] = None):
        """Initialize the Notion database manager.
        
        Args:
            client: The Notion client to use. If None, creates a new client.
        """
        self.db = get_db()
        self.config = self.db.get_config()
        self.client = client

    async def get_client(self) -> NotionClient:
        """Get the Notion client.
        
        Returns:
            The Notion client.
        """
        if not self.client:
            self.client = await get_notion_client()
        return self.client

    async def setup_databases(self, parent_page_id: str) -> Dict[str, str]:
        """Set up all required databases in Notion.
        
        Args:
            parent_page_id: The ID of the parent page.
            
        Returns:
            A dictionary mapping database types to their IDs.
        """
        client = await self.get_client()
        
        try:
            # Create the databases
            database_ids = await client.setup_notion_workspace(parent_page_id)
            
            # Update the schemas with the database IDs
            DAILY_LOG_SCHEMA.database_id = database_ids["daily_log"]
            PROBLEM_SOLUTION_SCHEMA.database_id = database_ids["problem_solution"]
            KNOWLEDGE_BASE_SCHEMA.database_id = database_ids["knowledge_base"]
            PROJECT_TRACKING_SCHEMA.database_id = database_ids["project_tracking"]
            
            logger.info(f"Set up Notion databases: {database_ids}")
            
            return database_ids
        except Exception as e:
            logger.error(f"Failed to set up Notion databases: {e}")
            raise NotionDatabaseError(f"Failed to set up Notion databases: {e}")

    async def validate_database_schema(self, database_id: str, expected_schema: NotionDatabaseSchema) -> bool:
        """Validate that a database has the expected schema.
        
        Args:
            database_id: The ID of the database to validate.
            expected_schema: The expected schema.
            
        Returns:
            True if the database has the expected schema, False otherwise.
        """
        client = await self.get_client()
        
        try:
            # Get the database
            database = await client.get_database(database_id)
            
            # Check the properties
            properties = database.get("properties", {})
            expected_properties = expected_schema.properties
            
            # Check that all expected properties exist
            for name, config in expected_properties.items():
                if name not in properties:
                    logger.warning(f"Database {database_id} is missing property {name}")
                    return False
                
                # Check the property type
                prop_type = next(iter(config.keys()))
                if prop_type not in properties[name]:
                    logger.warning(f"Database {database_id} property {name} has wrong type")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Failed to validate database schema: {e}")
            return False

    async def validate_all_databases(self) -> bool:
        """Validate that all required databases exist and have the expected schema.
        
        Returns:
            True if all databases are valid, False otherwise.
        """
        # Check if database IDs are configured
        if not self.config.notion_daily_log_db_id:
            logger.warning("Daily log database ID is not configured")
            return False
        
        if not self.config.notion_problem_solution_db_id:
            logger.warning("Problem solution database ID is not configured")
            return False
        
        if not self.config.notion_knowledge_base_db_id:
            logger.warning("Knowledge base database ID is not configured")
            return False
        
        if not self.config.notion_project_tracking_db_id:
            logger.warning("Project tracking database ID is not configured")
            return False
        
        # Update the schemas with the database IDs
        DAILY_LOG_SCHEMA.database_id = self.config.notion_daily_log_db_id
        PROBLEM_SOLUTION_SCHEMA.database_id = self.config.notion_problem_solution_db_id
        KNOWLEDGE_BASE_SCHEMA.database_id = self.config.notion_knowledge_base_db_id
        PROJECT_TRACKING_SCHEMA.database_id = self.config.notion_project_tracking_db_id
        
        # Validate each database
        daily_log_valid = await self.validate_database_schema(
            self.config.notion_daily_log_db_id, DAILY_LOG_SCHEMA
        )
        
        problem_solution_valid = await self.validate_database_schema(
            self.config.notion_problem_solution_db_id, PROBLEM_SOLUTION_SCHEMA
        )
        
        knowledge_base_valid = await self.validate_database_schema(
            self.config.notion_knowledge_base_db_id, KNOWLEDGE_BASE_SCHEMA
        )
        
        project_tracking_valid = await self.validate_database_schema(
            self.config.notion_project_tracking_db_id, PROJECT_TRACKING_SCHEMA
        )
        
        return daily_log_valid and problem_solution_valid and knowledge_base_valid and project_tracking_valid


async def get_database_manager() -> NotionDatabaseManager:
    """Get a Notion database manager.
    
    Returns:
        A Notion database manager.
    """
    client = await get_notion_client()
    return NotionDatabaseManager(client=client)
