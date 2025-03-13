"""
Notion sync module for DevJourney.

This module handles synchronization of insights with Notion databases.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import asyncio

from devjourney.database import get_db
from devjourney.models import (
    Conversation,
    Insight,
    InsightType,
    SyncStatus,
    NotionSyncRecord,
)
from devjourney.notion.client import NotionClient
from devjourney.notion.database import NotionDatabaseManager

logger = logging.getLogger(__name__)


class NotionSyncError(Exception):
    """Exception raised for Notion sync errors."""
    pass


class NotionSync:
    """Class for synchronizing insights with Notion."""

    def __init__(self):
        """Initialize the Notion sync."""
        self.db = get_db()
        self.config = self.db.get_config()
        self.notion_client = NotionClient()
        self.db_manager = NotionDatabaseManager(self.notion_client)

    def _format_insight_for_notion(self, insight: Insight) -> Dict[str, Any]:
        """Format an insight for Notion.
        
        Args:
            insight: The insight to format.
            
        Returns:
            A dictionary with the formatted insight.
        """
        # Get the conversation for this insight
        conversations = self.db.get_items(Conversation, id=insight.conversation_id)
        conversation = conversations[0] if conversations else None
        
        # Format the properties based on insight type
        properties = {}
        
        if insight.type == InsightType.PROBLEM_SOLUTION:
            properties = {
                "Title": {"title": [{"text": {"content": insight.title}}]},
                "Category": {"select": {"name": insight.category.value}},
                "Technologies": {"multi_select": [{"name": tech} for tech in self._extract_technologies(insight)]},
                "Confidence": {"number": insight.confidence_score},
                "Extracted At": {"date": {"start": insight.extracted_at.isoformat()}},
                "Last Synced": {"date": {"start": datetime.utcnow().isoformat()}},
            }
            
            # Add conversation reference if available
            if conversation:
                properties["Conversation"] = {
                    "rich_text": [{"text": {"content": f"ID: {conversation.id}\nSource: {conversation.source}\nTimestamp: {conversation.timestamp.isoformat()}"}}]
                }
        
        elif insight.type == InsightType.LEARNING:
            properties = {
                "Title": {"title": [{"text": {"content": insight.title}}]},
                "Category": {"select": {"name": insight.category.value}},
                "Technologies": {"multi_select": [{"name": tech} for tech in self._extract_technologies(insight)]},
                "Confidence": {"number": insight.confidence_score},
                "Extracted At": {"date": {"start": insight.extracted_at.isoformat()}},
                "Last Synced": {"date": {"start": datetime.utcnow().isoformat()}},
            }
            
            # Add conversation reference if available
            if conversation:
                properties["Conversation"] = {
                    "rich_text": [{"text": {"content": f"ID: {conversation.id}\nSource: {conversation.source}\nTimestamp: {conversation.timestamp.isoformat()}"}}]
                }
        
        elif insight.type == InsightType.CODE_REFERENCE:
            properties = {
                "Title": {"title": [{"text": {"content": insight.title}}]},
                "Category": {"select": {"name": insight.category.value}},
                "Technologies": {"multi_select": [{"name": tech} for tech in self._extract_technologies(insight)]},
                "Confidence": {"number": insight.confidence_score},
                "Extracted At": {"date": {"start": insight.extracted_at.isoformat()}},
                "Last Synced": {"date": {"start": datetime.utcnow().isoformat()}},
            }
            
            # Add conversation reference if available
            if conversation:
                properties["Conversation"] = {
                    "rich_text": [{"text": {"content": f"ID: {conversation.id}\nSource: {conversation.source}\nTimestamp: {conversation.timestamp.isoformat()}"}}]
                }
        
        elif insight.type == InsightType.PROJECT_REFERENCE:
            properties = {
                "Project": {"title": [{"text": {"content": insight.title.replace("Project: ", "")}}]},
                "Status": {"select": {"name": "In Progress"}},
                "Technologies": {"multi_select": [{"name": tech} for tech in self._extract_technologies(insight)]},
                "Start Date": {"date": {"start": insight.extracted_at.isoformat()}},
                "Last Updated": {"date": {"start": datetime.utcnow().isoformat()}},
            }
            
            # Add related insights
            properties["Related Insights"] = {
                "rich_text": [{"text": {"content": f"Insight ID: {insight.id}"}}]
            }
        
        return {
            "properties": properties,
            "children": self._format_insight_content_for_notion(insight),
        }

    def _format_insight_content_for_notion(self, insight: Insight) -> List[Dict[str, Any]]:
        """Format the content of an insight for Notion.
        
        Args:
            insight: The insight to format.
            
        Returns:
            A list of Notion block objects.
        """
        blocks = []
        
        # Add a heading
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": insight.title}}]
            }
        })
        
        # Add metadata
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": f"Type: {insight.type.value} | Category: {insight.category.value} | Confidence: {insight.confidence_score:.2f} | Extracted: {insight.extracted_at.isoformat()}"}
                    }
                ]
            }
        })
        
        # Add a divider
        blocks.append({"object": "block", "type": "divider", "divider": {}})
        
        # Add the content
        if insight.content:
            # Split content into paragraphs
            paragraphs = insight.content.split("\n\n")
            
            for paragraph in paragraphs:
                if not paragraph.strip():
                    continue
                
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": paragraph.strip()}}]
                    }
                })
        
        # Add code blocks
        if insight.code_blocks:
            for i, code_block in enumerate(insight.code_blocks):
                language = code_block.get("language", "")
                content = code_block.get("content", "")
                
                if not content.strip():
                    continue
                
                # Add a heading for the code block
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": f"Code Block {i+1}" + (f" ({language})" if language else "")}}]
                    }
                })
                
                # Add the code block
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": content}}],
                        "language": language.lower() if language else "plain text"
                    }
                })
        
        return blocks

    def _extract_technologies(self, insight: Insight) -> List[str]:
        """Extract technologies from an insight.
        
        Args:
            insight: The insight to extract technologies from.
            
        Returns:
            A list of technology names.
        """
        technologies = set()
        
        # Extract from code blocks
        if insight.code_blocks:
            for code_block in insight.code_blocks:
                language = code_block.get("language", "")
                if language:
                    technologies.add(language)
        
        # Get technology tags from the database
        insight_tags = self.db.get_technology_tags_for_insight(insight.id)
        for tag in insight_tags:
            technologies.add(tag.name)
        
        return list(technologies)

    def _get_notion_database_for_insight(self, insight: Insight) -> str:
        """Get the Notion database ID for an insight.
        
        Args:
            insight: The insight to get the database ID for.
            
        Returns:
            The Notion database ID.
        """
        # Get the database IDs from the config
        if insight.type == InsightType.PROBLEM_SOLUTION:
            return self.config.notion_problem_solution_db_id
        elif insight.type == InsightType.LEARNING:
            return self.config.notion_knowledge_base_db_id
        elif insight.type == InsightType.CODE_REFERENCE:
            return self.config.notion_knowledge_base_db_id
        elif insight.type == InsightType.PROJECT_REFERENCE:
            return self.config.notion_project_tracking_db_id
        else:
            return self.config.notion_knowledge_base_db_id

    def _get_existing_notion_page(self, insight: Insight) -> Optional[str]:
        """Get the existing Notion page ID for an insight.
        
        Args:
            insight: The insight to get the page ID for.
            
        Returns:
            The Notion page ID, or None if it doesn't exist.
        """
        # Check if there's a sync record for this insight
        sync_records = self.db.get_items(
            NotionSyncRecord,
            insight_id=insight.id,
        )
        
        if sync_records:
            return sync_records[0].notion_page_id
        
        return None

    def sync_insight(self, insight: Insight) -> Tuple[bool, str]:
        """Sync an insight with Notion.
        
        Args:
            insight: The insight to sync.
            
        Returns:
            A tuple of (success, message).
        """
        try:
            # Get the Notion database ID for this insight
            database_id = self._get_notion_database_for_insight(insight)
            
            if not database_id:
                return False, f"No Notion database configured for insight type {insight.type.value}"
            
            # Format the insight for Notion
            notion_data = self._format_insight_for_notion(insight)
            
            # Check if this insight has already been synced
            existing_page_id = self._get_existing_notion_page(insight)
            
            if existing_page_id:
                # Update the existing page
                response = self.notion_client.update_page(
                    existing_page_id,
                    notion_data["properties"],
                )
                
                # Update the page content
                self.notion_client.update_page_content(
                    existing_page_id,
                    notion_data["children"],
                )
                
                # Update the sync record
                sync_record = NotionSyncRecord(
                    insight_id=insight.id,
                    notion_page_id=existing_page_id,
                    last_synced=datetime.utcnow(),
                )
                self.db.update_or_create_item(sync_record, insight_id=insight.id)
                
                return True, f"Updated existing Notion page {existing_page_id} for insight {insight.id}"
            else:
                # Create a new page
                response = self.notion_client.create_page(
                    database_id,
                    notion_data["properties"],
                    notion_data["children"],
                )
                
                # Create a sync record
                sync_record = NotionSyncRecord(
                    insight_id=insight.id,
                    notion_page_id=response["id"],
                    last_synced=datetime.utcnow(),
                )
                self.db.add_item(sync_record)
                
                return True, f"Created new Notion page {response['id']} for insight {insight.id}"
        except Exception as e:
            logger.error(f"Failed to sync insight {insight.id} with Notion: {e}")
            return False, f"Failed to sync insight {insight.id} with Notion: {e}"

    def sync_daily_summary(self, date: Optional[datetime] = None) -> Tuple[bool, str]:
        """Sync a daily summary with Notion.
        
        Args:
            date: The date to sync the summary for. Defaults to today.
            
        Returns:
            A tuple of (success, message).
        """
        try:
            if not date:
                date = datetime.utcnow()
            
            # Get the start and end of the day
            start_of_day = datetime(date.year, date.month, date.day, 0, 0, 0)
            end_of_day = datetime(date.year, date.month, date.day, 23, 59, 59)
            
            # Get insights for the day
            insights = self.db.get_items(
                Insight,
                extracted_at_gte=start_of_day,
                extracted_at_lte=end_of_day,
                order_by="confidence_score",
                order_desc=True,
            )
            
            if not insights:
                return True, f"No insights found for {date.date().isoformat()}"
            
            # Group insights by type
            insights_by_type = {}
            for insight in insights:
                if insight.type not in insights_by_type:
                    insights_by_type[insight.type] = []
                insights_by_type[insight.type].append(insight)
            
            # Create a daily log entry in Notion
            properties = {
                "Date": {"date": {"start": date.date().isoformat()}},
                "Summary": {"rich_text": [{"text": {"content": f"Daily log for {date.date().isoformat()}"}}]},
                "Last Synced": {"date": {"start": datetime.utcnow().isoformat()}},
            }
            
            # Add counts for each insight type
            for insight_type in InsightType:
                count = len(insights_by_type.get(insight_type, []))
                if insight_type == InsightType.PROBLEM_SOLUTION:
                    properties["Problem Solutions"] = {"number": count}
                elif insight_type == InsightType.LEARNING:
                    properties["Learnings"] = {"number": count}
                elif insight_type == InsightType.CODE_REFERENCE:
                    properties["Code References"] = {"number": count}
                elif insight_type == InsightType.PROJECT_REFERENCE:
                    properties["Project References"] = {"number": count}
            
            # Create the content blocks
            blocks = []
            
            # Add a heading
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": f"Daily Log: {date.date().isoformat()}"}}]
                }
            })
            
            # Add a summary
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": f"Total insights: {len(insights)}"}
                        }
                    ]
                }
            })
            
            # Add sections for each insight type
            for insight_type in InsightType:
                type_insights = insights_by_type.get(insight_type, [])
                
                if not type_insights:
                    continue
                
                # Add a heading for this type
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": f"{insight_type.value} ({len(type_insights)})"}}]
                    }
                })
                
                # Add a bulleted list of insights
                for insight in type_insights:
                    # Get the Notion page ID for this insight
                    page_id = self._get_existing_notion_page(insight)
                    
                    if page_id:
                        # Add a link to the Notion page
                        blocks.append({
                            "object": "block",
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {"content": insight.title, "link": {"url": f"https://notion.so/{page_id.replace('-', '')}"}}
                                    }
                                ]
                            }
                        })
                    else:
                        # Add a plain text entry
                        blocks.append({
                            "object": "block",
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {
                                "rich_text": [{"type": "text", "text": {"content": insight.title}}]
                            }
                        })
            
            # Check if there's an existing daily log for this date
            existing_page_id = None
            
            # Query the daily log database for an entry with this date
            daily_log_db_id = self.config.notion_daily_log_db_id
            
            if daily_log_db_id:
                query_results = self.notion_client.query_database(
                    daily_log_db_id,
                    {
                        "filter": {
                            "property": "Date",
                            "date": {
                                "equals": date.date().isoformat()
                            }
                        }
                    }
                )
                
                if query_results.get("results"):
                    existing_page_id = query_results["results"][0]["id"]
            
            if existing_page_id:
                # Update the existing page
                response = self.notion_client.update_page(
                    existing_page_id,
                    properties,
                )
                
                # Update the page content
                self.notion_client.update_page_content(
                    existing_page_id,
                    blocks,
                )
                
                return True, f"Updated existing daily log for {date.date().isoformat()}"
            else:
                # Create a new page
                if not daily_log_db_id:
                    return False, "No Notion database configured for daily logs"
                
                response = self.notion_client.create_page(
                    daily_log_db_id,
                    properties,
                    blocks,
                )
                
                return True, f"Created new daily log for {date.date().isoformat()}"
        except Exception as e:
            logger.error(f"Failed to sync daily summary for {date.date().isoformat()}: {e}")
            return False, f"Failed to sync daily summary: {e}"

    def sync_insights(self, days: Optional[int] = None, limit: int = 50) -> Tuple[int, int, List[str]]:
        """Sync insights with Notion.
        
        Args:
            days: Filter by insights extracted in the last N days.
            limit: Maximum number of insights to sync.
            
        Returns:
            A tuple of (success_count, failure_count, error_messages).
        """
        try:
            # Build the filter parameters
            filter_params = {}
            
            if days:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                filter_params["extracted_at_gte"] = cutoff_date
            
            # Get insights to sync
            insights = self.db.get_items(
                Insight,
                **filter_params,
                limit=limit,
                order_by="extracted_at",
                order_desc=True,
            )
            
            if not insights:
                return 0, 0, ["No insights to sync"]
            
            success_count = 0
            failure_count = 0
            error_messages = []
            
            for insight in insights:
                success, message = self.sync_insight(insight)
                
                if success:
                    success_count += 1
                else:
                    failure_count += 1
                    error_messages.append(message)
            
            # Sync the daily summary for today
            self.sync_daily_summary()
            
            return success_count, failure_count, error_messages
        except Exception as e:
            logger.error(f"Failed to sync insights: {e}")
            return 0, 0, [f"Failed to sync insights: {e}"]

    def run_sync_job(self):
        """Run the sync job to synchronize insights with Notion."""
        try:
            # Update sync status
            sync_status = SyncStatus(
                component="notion_sync",
                status="running",
                last_run=datetime.utcnow(),
                details="Starting Notion sync job",
            )
            self.db.update_or_create_item(sync_status, component="notion_sync")
            
            start_time = time.time()
            
            # Validate Notion databases
            valid_databases = asyncio.run(self.db_manager.validate_all_databases())
            
            if not valid_databases:
                # Set up the databases
                # First, search for existing pages to find one to use as a parent
                logger.info("Searching for a page to use as parent...")
                search_results = asyncio.run(self.db_manager.client._make_request(
                    "POST",
                    "/search",
                    {
                        "filter": {
                            "property": "object",
                            "value": "page"
                        }
                    }
                ))
                
                # Check if we have any pages in the results
                if not search_results.get("results") or len(search_results.get("results")) == 0:
                    logger.error("No pages found in the workspace. Please create a page manually.")
                    raise NotionDatabaseError("No pages found in the workspace. Please create a page manually.")
                
                # Use the first page as parent
                parent_page_id = search_results["results"][0]["id"]
                asyncio.run(self.db_manager.setup_databases(parent_page_id))
            
            # Sync insights
            success_count, failure_count, error_messages = self.sync_insights(
                days=self.config.sync_days,
                limit=self.config.sync_batch_size,
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Update sync status
            status = "completed" if failure_count == 0 else "completed_with_errors"
            details = (
                f"Synced {success_count} insights with Notion in {duration:.2f} seconds. "
                f"{failure_count} failures."
            )
            
            if error_messages:
                details += f" Errors: {'; '.join(error_messages[:5])}"
                if len(error_messages) > 5:
                    details += f" and {len(error_messages) - 5} more."
            
            sync_status = SyncStatus(
                component="notion_sync",
                status=status,
                last_run=datetime.utcnow(),
                details=details,
            )
            self.db.update_or_create_item(sync_status, component="notion_sync")
            
            logger.info(
                f"Notion sync job completed in {duration:.2f} seconds. "
                f"Synced {success_count} insights with {failure_count} failures."
            )
        except Exception as e:
            logger.error(f"Notion sync job failed: {e}")
            
            # Update sync status
            sync_status = SyncStatus(
                component="notion_sync",
                status="failed",
                last_run=datetime.utcnow(),
                details=f"Notion sync job failed: {e}",
            )
            self.db.update_or_create_item(sync_status, component="notion_sync")
            
            raise NotionSyncError(f"Notion sync job failed: {e}")


def get_notion_sync() -> NotionSync:
    """Get a Notion sync instance.
    
    Returns:
        A Notion sync instance.
    """
    return NotionSync() 