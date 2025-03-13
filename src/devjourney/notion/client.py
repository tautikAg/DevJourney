"""
Notion API client for DevJourney.

This module implements a client for the Notion API to interact with Notion databases
and pages for storing and retrieving progress tracking data.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx
from pydantic import BaseModel
import asyncio

from devjourney.database import get_db
from devjourney.models import (
    Conversation,
    DailyLog,
    Insight,
    InsightCategory,
    InsightType,
    NotionDatabaseSchema,
)

logger = logging.getLogger(__name__)

# Notion API constants
NOTION_API_BASE_URL = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"


class NotionClientError(Exception):
    """Exception raised for Notion client errors."""
    pass


class NotionClient:
    """Client for interacting with the Notion API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Notion client.
        
        Args:
            api_key: The Notion API key. If None, uses the API key from the configuration.
        """
        self.db = get_db()
        self.config = self.db.get_config()
        self.api_key = api_key or self.config.notion_api_key
        
        if not self.api_key:
            raise NotionClientError("Notion API key is required")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_API_VERSION,
        }
        
        self.client = httpx.AsyncClient(
            base_url=NOTION_API_BASE_URL,
            headers=self.headers,
            timeout=30.0,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def _make_request(
        self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None,
        max_retries: int = 3, retry_delay: float = 1.0
    ) -> Dict[str, Any]:
        """Make a request to the Notion API.
        
        Args:
            method: The HTTP method to use.
            endpoint: The API endpoint to call.
            data: The data to send with the request.
            max_retries: Maximum number of retries for server errors.
            retry_delay: Base delay between retries in seconds.
            
        Returns:
            The response data.
            
        Raises:
            NotionClientError: If the request fails.
        """
        url = f"{NOTION_API_BASE_URL}{endpoint}"
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Making {method} request to {url}")
                if data:
                    logger.debug(f"Request data: {json.dumps(data, indent=2)}")
                
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method,
                        url,
                        headers=self.headers,
                        json=data,
                        timeout=30.0,
                    )
                    
                    logger.debug(f"Response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        return response.json()
                    else:
                        error_data = response.json() if response.content else {"message": "Unknown error"}
                        logger.error(f"API error: {response.status_code} - {error_data}")
                        
                        if response.status_code == 429:
                            # Rate limited, wait and retry
                            retry_after = int(response.headers.get("Retry-After", "1"))
                            logger.warning(f"Rate limited. Retrying after {retry_after} seconds.")
                            await asyncio.sleep(retry_after)
                            continue
                        
                        raise NotionClientError(f"API error: {response.status_code} - {error_data}")
            except (httpx.RequestError, asyncio.TimeoutError) as e:
                logger.error(f"Request error: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise NotionClientError(f"Request failed after {max_retries} attempts: {str(e)}")
        
        raise NotionClientError(f"Request failed after {max_retries} attempts")

    async def get_user(self) -> Dict[str, Any]:
        """Get the current user.
        
        Returns:
            The user data.
        """
        return await self._make_request("GET", "/users/me")

    async def list_databases(self) -> List[Dict[str, Any]]:
        """List all databases the user has access to.
        
        Returns:
            A list of databases.
        """
        response = await self._make_request("GET", "/search", {"filter": {"value": "database", "property": "object"}})
        return response.get("results", [])

    async def get_database(self, database_id: str) -> Dict[str, Any]:
        """Get a database by ID.
        
        Args:
            database_id: The database ID.
            
        Returns:
            The database data.
        """
        return await self._make_request("GET", f"/databases/{database_id}")

    async def query_database(
        self, database_id: str, filter_obj: Optional[Dict[str, Any]] = None, sorts: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Query a database.
        
        Args:
            database_id: The database ID.
            filter_obj: The filter to apply to the query.
            sorts: The sorts to apply to the query.
            
        Returns:
            A list of pages that match the query.
        """
        query_data: Dict[str, Any] = {}
        
        if filter_obj:
            query_data["filter"] = filter_obj
        
        if sorts:
            query_data["sorts"] = sorts
        
        response = await self._make_request("POST", f"/databases/{database_id}/query", query_data)
        return response.get("results", [])

    async def create_database(
        self, parent_page_id: str, title: str, properties: Dict[str, Any], description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new database.
        
        Args:
            parent_page_id: The ID of the parent page.
            title: The title of the database.
            properties: The properties of the database.
            description: The description of the database.
            
        Returns:
            The created database.
        """
        logger.info(f"Creating database '{title}' in parent page {parent_page_id}")
        
        # Log all property names to help debug
        logger.debug(f"Properties before modification: {list(properties.keys())}")
        
        # Check if there's already any property with a title type
        has_title_property = False
        title_property_name = None
        for prop_name, prop_value in properties.items():
            if "title" in prop_value:
                has_title_property = True
                title_property_name = prop_name
                logger.debug(f"Found title property: {prop_name}")
                break
        
        # If no title property exists, add one
        if not has_title_property:
            logger.debug("No title property found, adding one")
            properties["title"] = {"title": {}}
        else:
            logger.debug(f"Using existing title property: {title_property_name}")
        
        data = {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": properties,
        }
        
        if description:
            data["description"] = [{"type": "text", "text": {"content": description}}]
        
        logger.debug(f"Database creation data: {json.dumps(data, indent=2)}")
        
        try:
            result = await self._make_request("POST", "/databases", data)
            logger.info(f"Successfully created database '{title}' with ID: {result.get('id')}")
            return result
        except NotionClientError as e:
            logger.error(f"Failed to create database '{title}': {str(e)}")
            raise

    async def create_page(self, parent_id: str, properties: Dict[str, Any], content: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Create a new page.
        
        Args:
            parent_id: The ID of the parent (database or page).
            properties: The properties of the page.
            content: The content of the page.
            
        Returns:
            The created page.
        """
        data: Dict[str, Any] = {
            "parent": {"database_id": parent_id},
            "properties": properties,
        }
        
        if content:
            data["children"] = content
        
        return await self._make_request("POST", "/pages", data)

    async def update_page(self, page_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Update a page.
        
        Args:
            page_id: The ID of the page to update.
            properties: The properties to update.
            
        Returns:
            The updated page.
        """
        return await self._make_request("PATCH", f"/pages/{page_id}", {"properties": properties})

    async def get_page_content(self, page_id: str) -> List[Dict[str, Any]]:
        """Get the content of a page.
        
        Args:
            page_id: The ID of the page.
            
        Returns:
            The content of the page.
        """
        response = await self._make_request("GET", f"/blocks/{page_id}/children")
        return response.get("results", [])

    async def append_block_children(self, block_id: str, children: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Append blocks to a block.
        
        Args:
            block_id: The ID of the block to append to.
            children: The blocks to append.
            
        Returns:
            The response data.
        """
        return await self._make_request("PATCH", f"/blocks/{block_id}/children", {"children": children})

    async def create_daily_log_database(self, parent_page_id: str) -> str:
        """Create a daily log database.
        
        Args:
            parent_page_id: The ID of the parent page.
            
        Returns:
            The ID of the created database.
        """
        properties = {
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
        
        database = await self.create_database(
            parent_page_id=parent_page_id,
            title="DevJourney Daily Logs",
            properties=properties,
            description="Daily logs of your development journey"
        )
        
        database_id = database["id"]
        
        # Update the configuration with the database ID
        self.db.update_config(daily_log_database_id=database_id)
        
        return database_id

    async def create_problem_solution_database(self, parent_page_id: str) -> str:
        """Create a problem solution database.
        
        Args:
            parent_page_id: The ID of the parent page.
            
        Returns:
            The ID of the created database.
        """
        properties = {
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
        
        database = await self.create_database(
            parent_page_id=parent_page_id,
            title="DevJourney Problem Solutions",
            properties=properties,
            description="Problem solutions extracted from your conversations"
        )
        
        database_id = database["id"]
        
        # Update the configuration with the database ID
        self.db.update_config(problem_solution_database_id=database_id)
        
        return database_id

    async def create_knowledge_base_database(self, parent_page_id: str) -> str:
        """Create a knowledge base database.
        
        Args:
            parent_page_id: The ID of the parent page.
            
        Returns:
            The ID of the created database.
        """
        properties = {
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
        
        database = await self.create_database(
            parent_page_id=parent_page_id,
            title="DevJourney Knowledge Base",
            properties=properties,
            description="Knowledge base extracted from your conversations"
        )
        
        database_id = database["id"]
        
        # Update the configuration with the database ID
        self.db.update_config(knowledge_base_database_id=database_id)
        
        return database_id

    async def create_project_tracking_database(self, parent_page_id: str) -> str:
        """Create a project tracking database.
        
        Args:
            parent_page_id: The ID of the parent page.
            
        Returns:
            The ID of the created database.
        """
        properties = {
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
        
        database = await self.create_database(
            parent_page_id=parent_page_id,
            title="DevJourney Project Tracking",
            properties=properties,
            description="Track your development projects"
        )
        
        database_id = database["id"]
        
        # Update the configuration with the database ID
        self.db.update_config(project_tracking_database_id=database_id)
        
        return database_id

    async def setup_notion_workspace(self, parent_page_id: str) -> Dict[str, str]:
        """Set up the Notion workspace with all required databases.
        
        Args:
            parent_page_id: The ID of the parent page.
            
        Returns:
            A dictionary mapping database types to their IDs.
        """
        # Create the databases
        daily_log_db_id = await self.create_daily_log_database(parent_page_id)
        problem_solution_db_id = await self.create_problem_solution_database(parent_page_id)
        knowledge_base_db_id = await self.create_knowledge_base_database(parent_page_id)
        project_tracking_db_id = await self.create_project_tracking_database(parent_page_id)
        
        # Return the database IDs
        return {
            "daily_log": daily_log_db_id,
            "problem_solution": problem_solution_db_id,
            "knowledge_base": knowledge_base_db_id,
            "project_tracking": project_tracking_db_id,
        }

    async def sync_daily_log(self, daily_log: DailyLog) -> str:
        """Sync a daily log to Notion.
        
        Args:
            daily_log: The daily log to sync.
            
        Returns:
            The ID of the created or updated page.
        """
        database_id = self.config.daily_log_database_id
        if not database_id:
            raise NotionClientError("Daily log database ID is not configured")
        
        # Check if the daily log already exists in Notion
        if daily_log.notion_page_id:
            # Update the existing page
            properties = {
                "Summary": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": daily_log.summary}
                        }
                    ]
                },
                "Conversations": {
                    "number": daily_log.conversation_count
                },
                "Insights": {
                    "number": daily_log.insight_count
                },
                "Problem Solutions": {
                    "number": daily_log.problem_solution_count
                },
                "Learnings": {
                    "number": daily_log.learning_count
                },
                "Code References": {
                    "number": daily_log.code_reference_count
                },
                "Project References": {
                    "number": daily_log.project_reference_count
                },
                "Last Synced": {
                    "date": {
                        "start": datetime.utcnow().isoformat()
                    }
                }
            }
            
            page = await self.update_page(daily_log.notion_page_id, properties)
            return page["id"]
        else:
            # Create a new page
            properties = {
                "Date": {
                    "date": {
                        "start": daily_log.date.isoformat()
                    }
                },
                "Summary": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": daily_log.summary}
                        }
                    ]
                },
                "Conversations": {
                    "number": daily_log.conversation_count
                },
                "Insights": {
                    "number": daily_log.insight_count
                },
                "Problem Solutions": {
                    "number": daily_log.problem_solution_count
                },
                "Learnings": {
                    "number": daily_log.learning_count
                },
                "Code References": {
                    "number": daily_log.code_reference_count
                },
                "Project References": {
                    "number": daily_log.project_reference_count
                },
                "Last Synced": {
                    "date": {
                        "start": datetime.utcnow().isoformat()
                    }
                }
            }
            
            page = await self.create_page(database_id, properties)
            return page["id"]

    async def sync_insight(self, insight: Insight) -> str:
        """Sync an insight to Notion.
        
        Args:
            insight: The insight to sync.
            
        Returns:
            The ID of the created or updated page.
        """
        # Determine which database to use based on the insight type
        if insight.type == InsightType.PROBLEM_SOLUTION:
            database_id = self.config.problem_solution_database_id
            if not database_id:
                raise NotionClientError("Problem solution database ID is not configured")
        elif insight.type in [InsightType.LEARNING, InsightType.CODE_REFERENCE]:
            database_id = self.config.knowledge_base_database_id
            if not database_id:
                raise NotionClientError("Knowledge base database ID is not configured")
        elif insight.type == InsightType.PROJECT_REFERENCE:
            database_id = self.config.project_tracking_database_id
            if not database_id:
                raise NotionClientError("Project tracking database ID is not configured")
        else:
            raise NotionClientError(f"Unknown insight type: {insight.type}")
        
        # Get the conversation link
        conversation_link = f"Conversation ID: {insight.conversation_id}"
        if insight.conversation and insight.conversation.title:
            conversation_link = f"{insight.conversation.title} (ID: {insight.conversation_id})"
        
        # Prepare the content blocks
        content_blocks = []
        
        # Add the main content as a paragraph
        content_blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": insight.content}
                    }
                ]
            }
        })
        
        # Add code blocks if any
        for code_block in insight.code_blocks:
            language = code_block.get("language", "plain text")
            content = code_block.get("content", "")
            
            content_blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "language": language,
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": content}
                        }
                    ]
                }
            })
        
        # Check if the insight already exists in Notion
        if insight.notion_page_id:
            # Update the existing page
            properties = {
                "Title": {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": insight.title}
                        }
                    ]
                },
                "Category": {
                    "select": {
                        "name": insight.category.value
                    }
                },
                "Confidence": {
                    "number": insight.confidence_score
                },
                "Last Synced": {
                    "date": {
                        "start": datetime.utcnow().isoformat()
                    }
                }
            }
            
            # Add type for knowledge base
            if insight.type in [InsightType.LEARNING, InsightType.CODE_REFERENCE]:
                properties["Type"] = {
                    "select": {
                        "name": "Learning" if insight.type == InsightType.LEARNING else "Code Reference"
                    }
                }
            
            # Add conversation link
            properties["Conversation"] = {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": conversation_link}
                    }
                ]
            }
            
            # Update the page properties
            page = await self.update_page(insight.notion_page_id, properties)
            
            # Update the page content
            await self.append_block_children(insight.notion_page_id, content_blocks)
            
            return page["id"]
        else:
            # Create a new page
            properties = {
                "Title": {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": insight.title}
                        }
                    ]
                },
                "Category": {
                    "select": {
                        "name": insight.category.value
                    }
                },
                "Confidence": {
                    "number": insight.confidence_score
                },
                "Extracted At": {
                    "date": {
                        "start": insight.extracted_at.isoformat()
                    }
                },
                "Last Synced": {
                    "date": {
                        "start": datetime.utcnow().isoformat()
                    }
                }
            }
            
            # Add type for knowledge base
            if insight.type in [InsightType.LEARNING, InsightType.CODE_REFERENCE]:
                properties["Type"] = {
                    "select": {
                        "name": "Learning" if insight.type == InsightType.LEARNING else "Code Reference"
                    }
                }
            
            # Add conversation link
            properties["Conversation"] = {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": conversation_link}
                    }
                ]
            }
            
            # Create the page with content
            page = await self.create_page(database_id, properties, content_blocks)
            
            return page["id"]


async def get_notion_client() -> NotionClient:
    """Get a Notion client.
    
    Returns:
        A Notion client.
    """
    db = get_db()
    config = db.get_config()
    
    client = NotionClient(
        api_key=config.notion_api_key
    )
    
    return client
