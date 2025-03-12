"""
Notion API client for DevJourney.
"""
import logging
import time
from typing import Dict, List, Any, Optional, Union

from notion_client import Client, APIResponseError, APIErrorCode

from devjourney.config.settings import config
from devjourney.utils.credentials import get_notion_token

logger = logging.getLogger(__name__)


class NotionClient:
    """Client for interacting with the Notion API."""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the Notion client.
        
        Args:
            token: Notion API token (if None, will try to get from credentials)
        """
        self.token = token or get_notion_token()
        self.client = None
        self.logger = logging.getLogger(__name__)
        
        if self.token:
            self.client = Client(auth=self.token)
            self.logger.info("Initialized Notion client")
        else:
            self.logger.warning("Notion token not available")
    
    def is_available(self) -> bool:
        """
        Check if the Notion API is available.
        
        Returns:
            True if the Notion API is available, False otherwise
        """
        if not self.client:
            return False
        
        try:
            # Make a simple API call to check if the API is available
            self.client.users.me()
            return True
        except Exception as e:
            self.logger.warning(f"Notion API not available: {str(e)}")
            return False
    
    def create_database(self, parent_page_id: str, title: str, 
                       properties: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new database in Notion.
        
        Args:
            parent_page_id: ID of the parent page
            title: Title of the database
            properties: Database properties
            
        Returns:
            Created database or None if creation failed
        """
        if not self.is_available():
            self.logger.warning("Notion API not available")
            return None
        
        try:
            database = self.client.databases.create(
                parent={"page_id": parent_page_id},
                title=[{"type": "text", "text": {"content": title}}],
                properties=properties
            )
            
            self.logger.info(f"Created database '{title}' with ID {database['id']}")
            return database
        except APIResponseError as e:
            self.logger.error(f"Error creating database: {str(e)}")
            return None
    
    def get_database(self, database_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a database from Notion.
        
        Args:
            database_id: ID of the database
            
        Returns:
            Database or None if retrieval failed
        """
        if not self.is_available():
            self.logger.warning("Notion API not available")
            return None
        
        try:
            database = self.client.databases.retrieve(database_id=database_id)
            return database
        except APIResponseError as e:
            self.logger.error(f"Error getting database {database_id}: {str(e)}")
            return None
    
    def query_database(self, database_id: str, filter_obj: Optional[Dict[str, Any]] = None, 
                      sorts: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Query a database in Notion.
        
        Args:
            database_id: ID of the database
            filter_obj: Filter object for the query
            sorts: Sort specifications for the query
            
        Returns:
            List of pages from the database
        """
        if not self.is_available():
            self.logger.warning("Notion API not available")
            return []
        
        try:
            pages = []
            has_more = True
            start_cursor = None
            
            while has_more:
                query_params = {
                    "database_id": database_id,
                    "page_size": 100
                }
                
                if filter_obj:
                    query_params["filter"] = filter_obj
                
                if sorts:
                    query_params["sorts"] = sorts
                
                if start_cursor:
                    query_params["start_cursor"] = start_cursor
                
                response = self.client.databases.query(**query_params)
                
                pages.extend(response["results"])
                has_more = response["has_more"]
                start_cursor = response.get("next_cursor")
                
                # Rate limiting
                if has_more:
                    time.sleep(0.5)
            
            return pages
        except APIResponseError as e:
            self.logger.error(f"Error querying database {database_id}: {str(e)}")
            return []
    
    def create_page(self, database_id: str, properties: Dict[str, Any], 
                   content: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
        """
        Create a new page in a database.
        
        Args:
            database_id: ID of the database
            properties: Page properties
            content: Page content blocks
            
        Returns:
            Created page or None if creation failed
        """
        if not self.is_available():
            self.logger.warning("Notion API not available")
            return None
        
        try:
            page_data = {
                "parent": {"database_id": database_id},
                "properties": properties
            }
            
            if content:
                page_data["children"] = content
            
            page = self.client.pages.create(**page_data)
            
            self.logger.info(f"Created page with ID {page['id']}")
            return page
        except APIResponseError as e:
            self.logger.error(f"Error creating page: {str(e)}")
            return None
    
    def update_page(self, page_id: str, properties: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a page in Notion.
        
        Args:
            page_id: ID of the page
            properties: Updated page properties
            
        Returns:
            Updated page or None if update failed
        """
        if not self.is_available():
            self.logger.warning("Notion API not available")
            return None
        
        try:
            page = self.client.pages.update(page_id=page_id, properties=properties)
            
            self.logger.info(f"Updated page with ID {page_id}")
            return page
        except APIResponseError as e:
            self.logger.error(f"Error updating page {page_id}: {str(e)}")
            return None
    
    def get_page(self, page_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a page from Notion.
        
        Args:
            page_id: ID of the page
            
        Returns:
            Page or None if retrieval failed
        """
        if not self.is_available():
            self.logger.warning("Notion API not available")
            return None
        
        try:
            page = self.client.pages.retrieve(page_id=page_id)
            return page
        except APIResponseError as e:
            self.logger.error(f"Error getting page {page_id}: {str(e)}")
            return None
    
    def get_block_children(self, block_id: str) -> List[Dict[str, Any]]:
        """
        Get children of a block in Notion.
        
        Args:
            block_id: ID of the block
            
        Returns:
            List of child blocks
        """
        if not self.is_available():
            self.logger.warning("Notion API not available")
            return []
        
        try:
            blocks = []
            has_more = True
            start_cursor = None
            
            while has_more:
                query_params = {
                    "block_id": block_id,
                    "page_size": 100
                }
                
                if start_cursor:
                    query_params["start_cursor"] = start_cursor
                
                response = self.client.blocks.children.list(**query_params)
                
                blocks.extend(response["results"])
                has_more = response["has_more"]
                start_cursor = response.get("next_cursor")
                
                # Rate limiting
                if has_more:
                    time.sleep(0.5)
            
            return blocks
        except APIResponseError as e:
            self.logger.error(f"Error getting block children for {block_id}: {str(e)}")
            return []
    
    def append_block_children(self, block_id: str, children: List[Dict[str, Any]]) -> bool:
        """
        Append children to a block in Notion.
        
        Args:
            block_id: ID of the block
            children: Child blocks to append
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            self.logger.warning("Notion API not available")
            return False
        
        try:
            self.client.blocks.children.append(block_id=block_id, children=children)
            
            self.logger.info(f"Appended {len(children)} blocks to {block_id}")
            return True
        except APIResponseError as e:
            self.logger.error(f"Error appending blocks to {block_id}: {str(e)}")
            return False
    
    def delete_block(self, block_id: str) -> bool:
        """
        Delete a block in Notion.
        
        Args:
            block_id: ID of the block
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            self.logger.warning("Notion API not available")
            return False
        
        try:
            self.client.blocks.delete(block_id=block_id)
            
            self.logger.info(f"Deleted block {block_id}")
            return True
        except APIResponseError as e:
            self.logger.error(f"Error deleting block {block_id}: {str(e)}")
            return False
    
    def search(self, query: str, filter_obj: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search in Notion.
        
        Args:
            query: Search query
            filter_obj: Filter object for the search
            
        Returns:
            List of search results
        """
        if not self.is_available():
            self.logger.warning("Notion API not available")
            return []
        
        try:
            results = []
            has_more = True
            start_cursor = None
            
            while has_more:
                query_params = {
                    "query": query,
                    "page_size": 100
                }
                
                if filter_obj:
                    query_params["filter"] = filter_obj
                
                if start_cursor:
                    query_params["start_cursor"] = start_cursor
                
                response = self.client.search(**query_params)
                
                results.extend(response["results"])
                has_more = response["has_more"]
                start_cursor = response.get("next_cursor")
                
                # Rate limiting
                if has_more:
                    time.sleep(0.5)
            
            return results
        except APIResponseError as e:
            self.logger.error(f"Error searching for '{query}': {str(e)}")
            return []


# Singleton instance
notion_client = NotionClient() 