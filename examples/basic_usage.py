#!/usr/bin/env python3
"""
Basic usage example for DevJourney.

This script demonstrates how to use the DevJourney package
to extract, analyze, and sync development progress data.
"""
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import DevJourney modules
from devjourney.config.settings import config, update_config
from devjourney.extractors.factory import create_extractor
from devjourney.analyzers.analyzer import ConversationAnalyzer, analyze_recent_conversations
from devjourney.notion.sync import sync_to_notion

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def setup_example_config():
    """Set up a basic configuration for the example."""
    # Update Cursor extractor configuration
    update_config("extractors", "enabled", True)
    update_config("extractors", "cursor", {
        "enabled": True,
        "history_path": os.path.expanduser("~/Library/Application Support/Cursor/chat_history.json")
    })
    
    # Update analysis configuration
    update_config("analysis", "enabled", True)
    update_config("analysis", "llm", {
        "provider": "ollama",
        "model": "llama3",
        "temperature": 0.7,
        "max_tokens": 1000
    })
    
    logger.info("Example configuration set up")


def extract_conversations():
    """Extract conversations from configured sources."""
    logger.info("Extracting conversations")
    
    # Create a Cursor extractor
    extractor = create_extractor("cursor")
    
    # Extract conversations from the last 7 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    conversations = extractor.extract_conversations(start_date, end_date)
    
    logger.info(f"Extracted {len(conversations)} conversations")
    
    return conversations


def analyze_conversations(conversations):
    """Analyze extracted conversations."""
    logger.info("Analyzing conversations")
    
    # Create an analyzer
    analyzer = ConversationAnalyzer()
    
    # Analyze conversations
    results = analyzer.analyze(conversations)
    
    logger.info(f"Analysis complete: {len(results.items)} items found")
    
    return results


def sync_to_notion_if_configured(analysis_results):
    """Sync analysis results to Notion if configured."""
    if not config.get("notion", {}).get("enabled", False):
        logger.info("Notion integration not enabled, skipping sync")
        return
    
    if not config.get("notion", {}).get("api_token"):
        logger.info("Notion API token not configured, skipping sync")
        return
    
    logger.info("Syncing to Notion")
    sync_to_notion(analysis_results)
    logger.info("Notion sync complete")


def main():
    """Run the example."""
    logger.info("Starting DevJourney example")
    
    # Set up example configuration
    setup_example_config()
    
    # Extract conversations
    conversations = extract_conversations()
    
    # Analyze conversations
    analysis_results = analyze_conversations(conversations)
    
    # Sync to Notion if configured
    sync_to_notion_if_configured(analysis_results)
    
    logger.info("Example complete")


if __name__ == "__main__":
    main() 