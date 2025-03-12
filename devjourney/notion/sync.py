"""
Notion sync module for DevJourney.
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any

from devjourney.analyzers.analyzer import ConversationAnalyzer
from devjourney.config.settings import config
from devjourney.extractors.factory import create_extractor
from devjourney.notion.service import NotionService

logger = logging.getLogger(__name__)


def sync_to_notion(force: bool = False) -> Dict[str, Any]:
    """
    Sync recent conversations to Notion.
    
    Args:
        force: Force sync even if not scheduled
        
    Returns:
        Dictionary with sync results
    """
    try:
        # Check if sync is scheduled or forced
        if not force and not _is_sync_scheduled():
            return {
                "success": True,
                "items_synced": 0,
                "message": "Sync skipped - not scheduled"
            }
        
        # Get parent page ID from config
        parent_page_id = config.notion.get("parent_page_id")
        if not parent_page_id:
            return {
                "success": False,
                "error": "Notion parent page ID not configured"
            }
        
        # Create Notion service
        notion_service = NotionService()
        if not notion_service.is_available():
            return {
                "success": False,
                "error": "Notion API is not available"
            }
        
        # Extract conversations
        source = config.notion.get("source", "cursor")
        days = config.notion.get("days", 1)
        
        extractor = create_extractor(source)
        if not extractor:
            return {
                "success": False,
                "error": f"Unknown source: {source}"
            }
        
        # Configure extractor
        if source == "file" and "file_path" in config.notion:
            extractor.set_file_path(config.notion["file_path"])
        
        # Extract conversations
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"Extracting conversations from {start_date.date()} to {end_date.date()}")
        conversations = extractor.extract_conversations(start_date, end_date)
        
        if not conversations:
            return {
                "success": True,
                "items_synced": 0,
                "message": "No conversations found"
            }
        
        logger.info(f"Extracted {len(conversations)} conversations")
        
        # Analyze conversations
        analyzer = ConversationAnalyzer()
        result = analyzer.analyze_conversations(conversations)
        
        # Sync to Notion
        created_pages = notion_service.sync_analysis_result(result, parent_page_id)
        
        # Count total pages
        total_pages = sum(len(pages) for pages in created_pages.values())
        
        # Update last sync time
        _update_last_sync_time()
        
        return {
            "success": True,
            "items_synced": total_pages,
            "conversations_analyzed": len(conversations),
            "categories": {category.name: len(pages) for category, pages in created_pages.items() if pages}
        }
    
    except Exception as e:
        logger.exception("Error syncing to Notion")
        return {
            "success": False,
            "error": str(e)
        }


def _is_sync_scheduled() -> bool:
    """
    Check if sync is scheduled based on last sync time and frequency.
    
    Returns:
        True if sync is scheduled, False otherwise
    """
    last_sync = config.notion.get("last_sync")
    frequency = config.notion.get("sync_frequency", "daily")
    
    if not last_sync:
        return True
    
    last_sync_time = datetime.fromisoformat(last_sync)
    now = datetime.now()
    
    if frequency == "hourly":
        return (now - last_sync_time).total_seconds() >= 3600
    elif frequency == "daily":
        return (now - last_sync_time).total_seconds() >= 86400
    elif frequency == "weekly":
        return (now - last_sync_time).total_seconds() >= 604800
    else:
        return True


def _update_last_sync_time():
    """Update the last sync time in config."""
    config.notion["last_sync"] = datetime.now().isoformat()
    config.save() 