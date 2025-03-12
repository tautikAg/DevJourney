"""
Command-line interface for Notion integration.
"""
import argparse
import logging
import os
import sys
from datetime import datetime, timedelta

from devjourney.analyzers.analyzer import ConversationAnalyzer
from devjourney.extractors.factory import create_extractor
from devjourney.models.analysis import AnalysisResult
from devjourney.notion.service import NotionService

logger = logging.getLogger(__name__)


def setup_notion_parser(subparsers):
    """
    Set up the Notion command parser.
    
    Args:
        subparsers: Subparsers object from argparse
    """
    notion_parser = subparsers.add_parser(
        "notion", 
        help="Notion integration commands"
    )
    
    notion_subparsers = notion_parser.add_subparsers(
        dest="notion_command",
        help="Notion command to run"
    )
    
    # Setup command
    setup_parser = notion_subparsers.add_parser(
        "setup",
        help="Set up Notion integration"
    )
    setup_parser.add_argument(
        "--parent-page-id",
        required=True,
        help="Parent page ID to create databases in"
    )
    
    # Sync command
    sync_parser = notion_subparsers.add_parser(
        "sync",
        help="Sync data to Notion"
    )
    sync_parser.add_argument(
        "--parent-page-id",
        required=True,
        help="Parent page ID to create databases in if needed"
    )
    sync_parser.add_argument(
        "--source",
        choices=["cursor", "vscode", "file"],
        default="cursor",
        help="Source to extract conversations from"
    )
    sync_parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of days to analyze"
    )
    sync_parser.add_argument(
        "--file-path",
        help="Path to file containing conversations (only for file source)"
    )
    
    # Test command
    test_parser = notion_subparsers.add_parser(
        "test",
        help="Test Notion connection"
    )


def handle_notion_command(args):
    """
    Handle Notion commands.
    
    Args:
        args: Command-line arguments
    
    Returns:
        0 for success, non-zero for failure
    """
    if not args.notion_command:
        logger.error("No Notion command specified")
        return 1
    
    try:
        notion_service = NotionService()
        
        if args.notion_command == "test":
            if notion_service.is_available():
                logger.info("Notion API is available")
                return 0
            else:
                logger.error("Notion API is not available")
                return 1
        
        elif args.notion_command == "setup":
            database_ids = notion_service.setup_databases(args.parent_page_id)
            logger.info(f"Set up {len(database_ids)} databases in Notion")
            for name, db_id in database_ids.items():
                logger.info(f"  {name}: {db_id}")
            return 0
        
        elif args.notion_command == "sync":
            # Create extractor
            extractor = create_extractor(args.source)
            if not extractor:
                logger.error(f"Unknown source: {args.source}")
                return 1
            
            # Configure extractor
            if args.source == "file" and args.file_path:
                extractor.set_file_path(args.file_path)
            
            # Extract conversations
            end_date = datetime.now()
            start_date = end_date - timedelta(days=args.days)
            
            logger.info(f"Extracting conversations from {start_date.date()} to {end_date.date()}")
            conversations = extractor.extract_conversations(start_date, end_date)
            
            if not conversations:
                logger.warning("No conversations found")
                return 0
            
            logger.info(f"Extracted {len(conversations)} conversations")
            
            # Analyze conversations
            analyzer = ConversationAnalyzer()
            result = analyzer.analyze_conversations(conversations)
            
            # Sync to Notion
            created_pages = notion_service.sync_analysis_result(result, args.parent_page_id)
            
            # Log results
            total_pages = sum(len(pages) for pages in created_pages.values())
            logger.info(f"Created {total_pages} pages in Notion")
            for category, pages in created_pages.items():
                if pages:
                    logger.info(f"  {category.name}: {len(pages)} pages")
            
            return 0
        
        else:
            logger.error(f"Unknown Notion command: {args.notion_command}")
            return 1
    
    except Exception as e:
        logger.error(f"Error handling Notion command: {e}", exc_info=True)
        return 1 