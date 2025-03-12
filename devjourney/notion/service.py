git zdd """
Notion integration service for DevJourney.
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union

from devjourney.models.analysis import (
    ContentCategory, ContentItem, ProblemSolution, Learning, 
    CodeReference, MeetingNotes, DailySummary, AnalysisResult
)
from devjourney.notion.client import NotionClient
from devjourney.notion.formatter import NotionFormatter

logger = logging.getLogger(__name__)


class NotionService:
    """Service for integrating with Notion."""
    
    # Database names
    DB_DAILY_SUMMARIES = "DevJourney Daily Summaries"
    DB_PROBLEMS = "DevJourney Problems & Solutions"
    DB_LEARNINGS = "DevJourney Learnings"
    DB_CODE_REFERENCES = "DevJourney Code References"
    DB_MEETINGS = "DevJourney Meeting Notes"
    
    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize the Notion service.
        
        Args:
            api_token: Notion API token. If not provided, will try to get from environment.
        """
        self.api_token = api_token or os.environ.get("NOTION_API_TOKEN")
        if not self.api_token:
            raise ValueError("Notion API token is required. Set NOTION_API_TOKEN environment variable.")
        
        self.client = NotionClient(self.api_token)
        self.formatter = NotionFormatter()
        
        # Database IDs cache
        self._database_ids = {}
    
    def is_available(self) -> bool:
        """
        Check if Notion API is available.
        
        Returns:
            True if available, False otherwise
        """
        try:
            return self.client.is_available()
        except Exception as e:
            logger.error(f"Error checking Notion availability: {e}")
            return False
    
    def _get_or_create_database(self, name: str, properties: Dict[str, Dict[str, Any]], 
                               parent_page_id: Optional[str] = None) -> str:
        """
        Get or create a database with the given name.
        
        Args:
            name: Database name
            properties: Database properties
            parent_page_id: Parent page ID
            
        Returns:
            Database ID
        """
        if name in self._database_ids:
            return self._database_ids[name]
        
        # Search for existing database
        results = self.client.search(name, filter={"property": "object", "value": "database"})
        
        for result in results.get("results", []):
            if result.get("object") == "database" and result.get("title")[0]["plain_text"] == name:
                database_id = result["id"]
                self._database_ids[name] = database_id
                return database_id
        
        # Create new database if not found
        if not parent_page_id:
            raise ValueError("Parent page ID is required to create a new database")
        
        response = self.client.create_database(
            parent_page_id=parent_page_id,
            title=name,
            properties=properties
        )
        
        database_id = response["id"]
        self._database_ids[name] = database_id
        return database_id
    
    def setup_databases(self, parent_page_id: str) -> Dict[str, str]:
        """
        Set up all required databases.
        
        Args:
            parent_page_id: Parent page ID
            
        Returns:
            Dictionary of database names to IDs
        """
        # Daily Summaries database
        daily_summaries_props = {
            "Name": {"title": {}},
            "Date": {"date": {}},
            "Conversations": {"number": {}},
            "Problems Solved": {"number": {}},
            "Learnings": {"number": {}},
            "Code References": {"number": {}},
            "Meetings": {"number": {}},
            "Summary": {"rich_text": {}},
            "Highlights": {"rich_text": {}}
        }
        
        # Problems & Solutions database
        problems_props = {
            "Name": {"title": {}},
            "Date": {"date": {}},
            "Problem": {"rich_text": {}},
            "Solution": {"rich_text": {}},
            "Tags": {"multi_select": {}},
            "Source": {"select": {}}
        }
        
        # Learnings database
        learnings_props = {
            "Name": {"title": {}},
            "Date": {"date": {}},
            "Concept": {"rich_text": {}},
            "Explanation": {"rich_text": {}},
            "Examples": {"rich_text": {}},
            "Tags": {"multi_select": {}},
            "Source": {"select": {}}
        }
        
        # Code References database
        code_refs_props = {
            "Name": {"title": {}},
            "Date": {"date": {}},
            "Language": {"select": {}},
            "Code": {"rich_text": {}},
            "Explanation": {"rich_text": {}},
            "File Path": {"rich_text": {}},
            "Tags": {"multi_select": {}},
            "Source": {"select": {}}
        }
        
        # Meeting Notes database
        meetings_props = {
            "Name": {"title": {}},
            "Date": {"date": {}},
            "Participants": {"rich_text": {}},
            "Action Items": {"rich_text": {}},
            "Decisions": {"rich_text": {}},
            "Tags": {"multi_select": {}},
            "Source": {"select": {}}
        }
        
        # Create or get all databases
        database_ids = {
            self.DB_DAILY_SUMMARIES: self._get_or_create_database(
                self.DB_DAILY_SUMMARIES, daily_summaries_props, parent_page_id
            ),
            self.DB_PROBLEMS: self._get_or_create_database(
                self.DB_PROBLEMS, problems_props, parent_page_id
            ),
            self.DB_LEARNINGS: self._get_or_create_database(
                self.DB_LEARNINGS, learnings_props, parent_page_id
            ),
            self.DB_CODE_REFERENCES: self._get_or_create_database(
                self.DB_CODE_REFERENCES, code_refs_props, parent_page_id
            ),
            self.DB_MEETINGS: self._get_or_create_database(
                self.DB_MEETINGS, meetings_props, parent_page_id
            )
        }
        
        self._database_ids.update(database_ids)
        return database_ids
    
    def _create_page_with_content(self, database_id: str, properties: Dict[str, Dict[str, Any]], 
                                 content: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a page with content.
        
        Args:
            database_id: Database ID
            properties: Page properties
            content: Page content blocks
            
        Returns:
            Created page
        """
        # Create the page
        page = self.client.create_page(database_id=database_id, properties=properties)
        
        # Add content blocks
        if content:
            self.client.append_block_children(page["id"], content)
        
        return page
    
    def create_daily_summary(self, summary: DailySummary) -> Dict[str, Any]:
        """
        Create a daily summary page.
        
        Args:
            summary: Daily summary
            
        Returns:
            Created page
        """
        if self.DB_DAILY_SUMMARIES not in self._database_ids:
            raise ValueError(f"Database {self.DB_DAILY_SUMMARIES} not set up")
        
        # Check if summary for this date already exists
        date_str = summary.date.strftime("%Y-%m-%d")
        results = self.client.query_database(
            self._database_ids[self.DB_DAILY_SUMMARIES],
            filter={
                "property": "Date",
                "date": {
                    "equals": date_str
                }
            }
        )
        
        if results.get("results"):
            # Update existing page
            page_id = results["results"][0]["id"]
            properties = NotionFormatter.format_daily_summary(summary)
            page = self.client.update_page(page_id, properties=properties)
            
            # Replace content
            content = NotionFormatter.format_daily_summary_content(summary)
            # TODO: Implement block replacement logic when needed
            
            return page
        
        # Create new page
        properties = NotionFormatter.format_daily_summary(summary)
        content = NotionFormatter.format_daily_summary_content(summary)
        
        return self._create_page_with_content(
            self._database_ids[self.DB_DAILY_SUMMARIES],
            properties,
            content
        )
    
    def create_problem_solution(self, problem: ProblemSolution) -> Dict[str, Any]:
        """
        Create a problem solution page.
        
        Args:
            problem: Problem solution
            
        Returns:
            Created page
        """
        if self.DB_PROBLEMS not in self._database_ids:
            raise ValueError(f"Database {self.DB_PROBLEMS} not set up")
        
        properties = NotionFormatter.format_problem_solution(problem)
        content = NotionFormatter.format_problem_solution_content(problem)
        
        return self._create_page_with_content(
            self._database_ids[self.DB_PROBLEMS],
            properties,
            content
        )
    
    def create_learning(self, learning: Learning) -> Dict[str, Any]:
        """
        Create a learning page.
        
        Args:
            learning: Learning
            
        Returns:
            Created page
        """
        if self.DB_LEARNINGS not in self._database_ids:
            raise ValueError(f"Database {self.DB_LEARNINGS} not set up")
        
        properties = NotionFormatter.format_learning(learning)
        content = NotionFormatter.format_learning_content(learning)
        
        return self._create_page_with_content(
            self._database_ids[self.DB_LEARNINGS],
            properties,
            content
        )
    
    def create_code_reference(self, code_ref: CodeReference) -> Dict[str, Any]:
        """
        Create a code reference page.
        
        Args:
            code_ref: Code reference
            
        Returns:
            Created page
        """
        if self.DB_CODE_REFERENCES not in self._database_ids:
            raise ValueError(f"Database {self.DB_CODE_REFERENCES} not set up")
        
        properties = NotionFormatter.format_code_reference(code_ref)
        content = NotionFormatter.format_code_reference_content(code_ref)
        
        return self._create_page_with_content(
            self._database_ids[self.DB_CODE_REFERENCES],
            properties,
            content
        )
    
    def create_meeting_notes(self, meeting: MeetingNotes) -> Dict[str, Any]:
        """
        Create a meeting notes page.
        
        Args:
            meeting: Meeting notes
            
        Returns:
            Created page
        """
        if self.DB_MEETINGS not in self._database_ids:
            raise ValueError(f"Database {self.DB_MEETINGS} not set up")
        
        properties = NotionFormatter.format_meeting_notes(meeting)
        content = NotionFormatter.format_meeting_notes_content(meeting)
        
        return self._create_page_with_content(
            self._database_ids[self.DB_MEETINGS],
            properties,
            content
        )
    
    def create_content_item(self, item: ContentItem) -> Dict[str, Any]:
        """
        Create a page for a content item.
        
        Args:
            item: Content item
            
        Returns:
            Created page
        """
        if isinstance(item, ProblemSolution):
            return self.create_problem_solution(item)
        elif isinstance(item, Learning):
            return self.create_learning(item)
        elif isinstance(item, CodeReference):
            return self.create_code_reference(item)
        elif isinstance(item, MeetingNotes):
            return self.create_meeting_notes(item)
        else:
            raise ValueError(f"Unsupported content item type: {type(item)}")
    
    def sync_analysis_result(self, result: AnalysisResult, parent_page_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Sync an analysis result to Notion.
        
        Args:
            result: Analysis result
            parent_page_id: Parent page ID for creating databases if needed
            
        Returns:
            Dictionary of created pages by category
        """
        # Ensure databases are set up
        if not self._database_ids:
            self.setup_databases(parent_page_id)
        
        created_pages = {
            ContentCategory.PROBLEM_SOLUTION: [],
            ContentCategory.LEARNING: [],
            ContentCategory.CODE_REFERENCE: [],
            ContentCategory.MEETING_NOTES: []
        }
        
        # Create pages for each content item
        for category, items in result.items_by_category.items():
            for item in items:
                try:
                    page = self.create_content_item(item)
                    created_pages[category].append(page)
                except Exception as e:
                    logger.error(f"Error creating page for {category} item: {e}")
        
        # Create daily summary if available
        if result.daily_summary:
            try:
                self.create_daily_summary(result.daily_summary)
            except Exception as e:
                logger.error(f"Error creating daily summary: {e}")
        
        return created_pages 