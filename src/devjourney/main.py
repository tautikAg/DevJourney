"""
Main module for DevJourney.

This module coordinates all components of the application.
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from dotenv import load_dotenv

from devjourney.database import get_db, init_db
from devjourney.models import SyncStatus
from devjourney.extractors.cursor import get_cursor_extractor
from devjourney.mcp.client import ClaudeMCPClient
from devjourney.analysis.main import run_analysis_job, process_specific_conversation
from devjourney.analysis.insights import get_insights, get_daily_summary, get_insight_stats
from devjourney.notion.sync import get_notion_sync
from devjourney.notion.database import get_database_manager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("devjourney.log"),
    ],
)

logger = logging.getLogger(__name__)


def setup_environment():
    """Set up the environment for the application."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Initialize the database
    init_db()
    
    # Check if the database is initialized
    db = get_db()
    
    # Check if the config is set up
    config = db.get_config()
    
    if not config:
        logger.error("Config not found. Please set up the config first.")
        sys.exit(1)
    
    # Update config with environment variables
    env_updates = {}
    
    if os.getenv("NOTION_API_KEY"):
        env_updates["notion_api_key"] = os.getenv("NOTION_API_KEY")
    
    if os.getenv("CLAUDE_API_KEY"):
        env_updates["claude_api_key"] = os.getenv("CLAUDE_API_KEY")
    
    if os.getenv("NOTION_DAILY_LOG_DB_ID"):
        env_updates["notion_daily_log_db_id"] = os.getenv("NOTION_DAILY_LOG_DB_ID")
    
    if os.getenv("NOTION_PROBLEM_SOLUTION_DB_ID"):
        env_updates["notion_problem_solution_db_id"] = os.getenv("NOTION_PROBLEM_SOLUTION_DB_ID")
    
    if os.getenv("NOTION_KNOWLEDGE_BASE_DB_ID"):
        env_updates["notion_knowledge_base_db_id"] = os.getenv("NOTION_KNOWLEDGE_BASE_DB_ID")
    
    if os.getenv("NOTION_PROJECT_TRACKING_DB_ID"):
        env_updates["notion_project_tracking_db_id"] = os.getenv("NOTION_PROJECT_TRACKING_DB_ID")
    
    if env_updates:
        db.update_config(**env_updates)
        # Refresh config
        config = db.get_config()
    
    # Check if the Notion API key is set
    if not config.notion_api_key:
        logger.warning("Notion API key not set. Notion sync will not work.")
    
    # Check if the Claude API key is set
    if not config.claude_api_key:
        logger.warning("Claude API key not set. Claude integration will not work.")
    
    logger.info("Environment set up successfully.")


def extract_conversations(days: Optional[int] = None):
    """Extract conversations from all sources.
    
    Args:
        days: Extract conversations from the last N days.
    """
    logger.info("Extracting conversations...")
    
    # Update sync status
    db = get_db()
    sync_status = SyncStatus(
        component="extraction",
        status="running",
        last_run=datetime.utcnow(),
        details="Starting extraction job",
    )
    db.update_or_create_item(sync_status, component="extraction")
    
    start_time = time.time()
    
    # Extract from Cursor
    try:
        cursor_extractor = get_cursor_extractor()
        cursor_conversations = cursor_extractor.extract_conversations(days=days)
        logger.info(f"Extracted {len(cursor_conversations)} conversations from Cursor")
    except Exception as e:
        logger.error(f"Failed to extract conversations from Cursor: {e}")
        cursor_conversations = []
    
    # Extract from Claude
    try:
        claude_client = ClaudeMCPClient()
        claude_conversations = claude_client.extract_conversations(days=days)
        logger.info(f"Extracted {len(claude_conversations)} conversations from Claude")
    except Exception as e:
        logger.error(f"Failed to extract conversations from Claude: {e}")
        claude_conversations = []
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Update sync status
    total_conversations = len(cursor_conversations) + len(claude_conversations)
    sync_status = SyncStatus(
        component="extraction",
        status="completed",
        last_run=datetime.utcnow(),
        details=f"Extracted {total_conversations} conversations in {duration:.2f} seconds",
    )
    db.update_or_create_item(sync_status, component="extraction")
    
    logger.info(f"Extraction completed in {duration:.2f} seconds. Extracted {total_conversations} conversations.")


def analyze_conversations():
    """Analyze conversations and extract insights."""
    logger.info("Analyzing conversations...")
    
    # Run the analysis job
    run_analysis_job()


def sync_with_notion():
    """Sync insights with Notion."""
    logger.info("Syncing with Notion...")
    
    # Get the Notion sync instance
    notion_sync = get_notion_sync()
    
    # Run the sync job
    notion_sync.run_sync_job()


def run_full_sync(days: Optional[int] = None):
    """Run a full sync of all components.
    
    Args:
        days: Sync data from the last N days.
    """
    logger.info("Running full sync...")
    
    # Set up the environment
    setup_environment()
    
    # Extract conversations
    extract_conversations(days=days)
    
    # Analyze conversations
    analyze_conversations()
    
    # Sync with Notion
    sync_with_notion()
    
    logger.info("Full sync completed.")


def get_status() -> Dict[str, Any]:
    """Get the status of all components.
    
    Returns:
        A dictionary with the status of all components.
    """
    db = get_db()
    
    # Get all sync statuses
    sync_statuses = db.get_items(SyncStatus)
    
    # Build the status dictionary
    status = {
        "components": {},
        "last_full_sync": None,
        "insights": {},
    }
    
    # Add component statuses
    for sync_status in sync_statuses:
        status["components"][sync_status.component] = {
            "status": sync_status.status,
            "last_run": sync_status.last_run.isoformat() if sync_status.last_run else None,
            "details": sync_status.details,
        }
    
    # Get the last full sync time
    extraction_status = next((s for s in sync_statuses if s.component == "extraction"), None)
    analysis_status = next((s for s in sync_statuses if s.component == "analysis"), None)
    notion_sync_status = next((s for s in sync_statuses if s.component == "notion_sync"), None)
    
    if extraction_status and analysis_status and notion_sync_status:
        # Get the oldest last run time
        last_runs = [
            s.last_run for s in [extraction_status, analysis_status, notion_sync_status]
            if s.last_run
        ]
        
        if last_runs:
            status["last_full_sync"] = min(last_runs).isoformat()
    
    # Get insight stats
    try:
        insight_stats = get_insight_stats()
        status["insights"] = insight_stats
    except Exception as e:
        logger.error(f"Failed to get insight stats: {e}")
    
    return status


async def setup_notion():
    """Set up Notion workspace with DevJourney page and databases."""
    import asyncio
    
    logger.info("Setting up Notion workspace...")
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Check if Notion API key is set
    db = get_db()
    config = db.get_config()
    
    # Update config with environment variables
    if os.getenv("NOTION_API_KEY"):
        config.notion_api_key = os.getenv("NOTION_API_KEY")
        db.update_config_object(config)
    
    if not config.notion_api_key:
        logger.error("Notion API key is not set. Please set it in the .env file or update the config.")
        print("\nTo set up Notion integration, you need to:")
        print("1. Create a Notion integration at https://www.notion.so/my-integrations")
        print("2. Copy the Internal Integration Token")
        print("3. Add it to your .env file as NOTION_API_KEY=your_token_here")
        print("4. Run this command again")
        return False
    
    # Get the database manager
    db_manager = await get_database_manager()
    
    # Get the Notion client
    client = await db_manager.get_client()
    
    try:
        # First, search for existing pages to find one to use as a parent
        logger.info("Searching for a page to use as parent...")
        search_results = await client._make_request(
            "POST",
            "/search",
            {
                "filter": {
                    "property": "object",
                    "value": "page"
                }
            }
        )
        
        # Check if we have any pages in the results
        if not search_results.get("results") or len(search_results.get("results")) == 0:
            logger.error("No pages found in the workspace. Please create a page in Notion and share it with the integration.")
            print("\nTo set up DevJourney in Notion, follow these steps:")
            print("1. Go to your Notion workspace")
            print("2. Click '+ New page' in the sidebar")
            print("3. Create a page (e.g., name it 'DevJourney')")
            print("4. Click 'Share' in the top right corner")
            print("5. In the 'Add people, groups, or integrations' field, search for your integration name")
            print("6. Select your integration and click 'Invite'")
            print("7. Run this command again")
            return False
        
        # Use the first page as parent
        parent_page_id = search_results["results"][0]["id"]
        parent_page_title = search_results["results"][0].get("properties", {}).get("title", {}).get("title", [{}])[0].get("text", {}).get("content", "Unknown Page")
        logger.info(f"Using existing page '{parent_page_title}' with ID: {parent_page_id} as parent")
        
        # Set up the databases
        logger.info("Setting up Notion databases...")
        database_ids = await db_manager.setup_databases(parent_page_id)
        
        # Update the config with the database IDs
        db = get_db()
        config = db.get_config()
        
        config.notion_daily_log_db_id = database_ids["daily_log"]
        config.notion_problem_solution_db_id = database_ids["problem_solution"]
        config.notion_knowledge_base_db_id = database_ids["knowledge_base"]
        config.notion_project_tracking_db_id = database_ids["project_tracking"]
        
        db.update_config_object(config)
        
        logger.info("Notion workspace set up successfully!")
        logger.info(f"DevJourney databases have been created in your Notion workspace.")
        logger.info(f"You can access them at: https://notion.so/{parent_page_id.replace('-', '')}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to set up Notion workspace: {e}")
        return False


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="DevJourney - Personal Progress Tracking System")
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Set up the environment")
    
    # Setup Notion command
    setup_notion_parser = subparsers.add_parser("setup-notion", help="Set up Notion workspace with DevJourney page and databases")
    
    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract conversations")
    extract_parser.add_argument("--days", type=int, help="Extract conversations from the last N days")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze conversations")
    
    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync insights with Notion")
    
    # Full sync command
    full_sync_parser = subparsers.add_parser("full-sync", help="Run a full sync of all components")
    full_sync_parser.add_argument("--days", type=int, help="Sync data from the last N days")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Get the status of all components")
    
    # Watch command
    watch_parser = subparsers.add_parser("watch", help="Watch for changes in Cursor chat history")
    
    # Process command
    process_parser = subparsers.add_parser("process", help="Process a specific conversation")
    process_parser.add_argument("conversation_id", help="ID of the conversation to process")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Run the appropriate command
    if args.command == "setup":
        setup_environment()
    elif args.command == "setup-notion":
        import asyncio
        success = asyncio.run(setup_notion())
        if success:
            logger.info("Notion workspace set up successfully!")
        else:
            logger.error("Failed to set up Notion workspace.")
            sys.exit(1)
    elif args.command == "extract":
        extract_conversations(days=args.days)
    elif args.command == "analyze":
        analyze_conversations()
    elif args.command == "sync":
        sync_with_notion()
    elif args.command == "full-sync":
        run_full_sync(days=args.days)
    elif args.command == "status":
        status = get_status()
        print("DevJourney Status:")
        print(f"Last full sync: {status.get('last_full_sync', 'Never')}")
        print("\nComponents:")
        for component, component_status in status.get("components", {}).items():
            print(f"  {component}: {component_status.get('status', 'Unknown')} (Last run: {component_status.get('last_run', 'Never')})")
            print(f"    {component_status.get('details', '')}")
        print("\nInsights:")
        insights = status.get("insights", {})
        print(f"  Total: {insights.get('total', 0)}")
        print("  By type:")
        for type_name, count in insights.get("by_type", {}).items():
            print(f"    {type_name}: {count}")
        print("  By category:")
        for category_name, count in insights.get("by_category", {}).items():
            print(f"    {category_name}: {count}")
    elif args.command == "watch":
        # Set up the cursor extractor
        cursor_extractor = get_cursor_extractor()
        
        # Define the callback function
        def on_change(changes):
            logger.info(f"Detected {len(changes)} changes in Cursor chat history")
            extract_conversations(days=1)
            analyze_conversations()
            sync_with_notion()
        
        # Watch for changes
        logger.info("Watching for changes in Cursor chat history...")
        cursor_extractor.watch_for_changes(on_change)
    elif args.command == "process":
        # Process a specific conversation
        conversation = process_specific_conversation(args.conversation_id)
        
        if conversation:
            logger.info(f"Processed conversation {conversation.id}")
            
            # Sync with Notion
            notion_sync = get_notion_sync()
            notion_sync.sync_insights(days=1)
        else:
            logger.error(f"Conversation {args.conversation_id} not found")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
