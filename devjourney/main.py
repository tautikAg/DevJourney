#!/usr/bin/env python3
"""
DevJourney - A personal progress tracking system.

This module serves as the main entry point for the DevJourney application.
"""
from __future__ import annotations

import os
import sys
import logging
from typing import Any, Dict
import click
import argparse
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler

from devjourney.config.settings import config, CONFIG_DIR, LOG_DIR
from devjourney.cli.notion_commands import setup_notion_parser, handle_notion_command

# Set up logging
log_file = LOG_DIR / "devjourney.log"
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RichHandler(rich_tracebacks=True),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger("devjourney")
console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """DevJourney - Track your development progress from AI conversations."""
    pass


@cli.command()
def setup() -> None:
    """Run the setup wizard to configure DevJourney."""
    from devjourney.ui.setup_wizard import run_setup_wizard
    console.print("[bold green]Starting DevJourney setup wizard...[/bold green]")
    run_setup_wizard()


@cli.command()
@click.option("--headless", is_flag=True, help="Run in headless mode without UI")
def start(headless: bool) -> None:
    """Start the DevJourney application."""
    if headless:
        console.print("[bold green]Starting DevJourney in headless mode...[/bold green]")
        # Start background services without UI
        from devjourney.utils.service_manager import start_services
        start_services()
    else:
        console.print("[bold green]Starting DevJourney application...[/bold green]")
        # Start the UI application
        from devjourney.ui.app import start_app
        start_app()


@cli.command()
def status() -> None:
    """Check the status of DevJourney services."""
    from devjourney.utils.service_manager import check_status
    status_info = check_status()
    
    console.print("[bold]DevJourney Status[/bold]")
    console.print(f"Configuration: {CONFIG_DIR}")
    
    for service, status in status_info.items():
        color = "green" if status["running"] else "red"
        status_text = "Running" if status["running"] else "Stopped"
        console.print(f"[bold]{service}[/bold]: [{color}]{status_text}[/{color}]")
        if "details" in status:
            console.print(f"  {status['details']}")


@cli.command()
@click.option("--force", is_flag=True, help="Force sync even if not scheduled")
def sync(force: bool) -> None:
    """Manually trigger a sync with Notion."""
    from devjourney.notion.sync import sync_to_notion
    
    console.print("[bold]Manually triggering Notion sync...[/bold]")
    result = sync_to_notion(force=force)
    
    # Using if-else instead of match statement for better compatibility
    if result.get("success", False):
        console.print(f"[bold green]Sync completed successfully![/bold green]")
        console.print(f"Items synced: {result.get('items_synced', 0)}")
        if "message" in result:
            console.print(f"Message: {result['message']}")
    else:
        console.print(f"[bold red]Sync failed![/bold red]")
        console.print(f"Error: {result.get('error', 'Unknown error')}")


@cli.command()
@click.option("--days", default=7, help="Number of days to analyze")
def analyze(days: int) -> None:
    """Analyze recent conversations without syncing to Notion."""
    from devjourney.analyzers.analyzer import analyze_recent_conversations
    
    console.print(f"[bold]Analyzing conversations from the last {days} days...[/bold]")
    result = analyze_recent_conversations(days=days)
    
    console.print(f"[bold green]Analysis complete![/bold green]")
    console.print(f"Conversations analyzed: {result['conversations_analyzed']}")
    console.print(f"Problems identified: {result['problems_identified']}")
    console.print(f"Learnings extracted: {result['learnings_extracted']}")
    console.print(f"Code references found: {result['code_references']}")


@cli.group()
def notion() -> None:
    """Notion integration commands."""
    pass


@notion.command()
@click.option("--parent-page-id", required=True, help="Parent page ID to create databases in")
def setup_notion(parent_page_id: str) -> None:
    """Set up Notion integration."""
    from devjourney.notion.service import NotionService
    
    console.print("[bold]Setting up Notion integration...[/bold]")
    try:
        notion_service = NotionService()
        database_ids = notion_service.setup_databases(parent_page_id)
        
        console.print(f"[bold green]Set up {len(database_ids)} databases in Notion![/bold green]")
        for name, db_id in database_ids.items():
            console.print(f"  {name}: {db_id}")
    except Exception as e:
        console.print(f"[bold red]Error setting up Notion integration:[/bold red] {str(e)}")


@notion.command()
@click.option("--parent-page-id", required=True, help="Parent page ID to create databases in if needed")
@click.option("--source", type=click.Choice(["cursor", "vscode", "file"]), default="cursor", 
              help="Source to extract conversations from")
@click.option("--days", default=1, type=int, help="Number of days to analyze")
@click.option("--file-path", help="Path to file containing conversations (only for file source)")
def sync_notion(parent_page_id: str, source: str, days: int, file_path: str | None) -> None:
    """Sync data to Notion."""
    from devjourney.extractors.factory import create_extractor
    from devjourney.analyzers.analyzer import ConversationAnalyzer
    from devjourney.notion.service import NotionService
    from datetime import datetime, timedelta
    
    console.print("[bold]Syncing data to Notion...[/bold]")
    try:
        # Create extractor
        extractor = create_extractor(source)
        if not extractor:
            console.print(f"[bold red]Unknown source:[/bold red] {source}")
            return
        
        # Configure extractor
        if source == "file" and file_path:
            extractor.set_file_path(file_path)
        
        # Extract conversations
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        console.print(f"Extracting conversations from {start_date.date()} to {end_date.date()}")
        conversations = extractor.extract_conversations(start_date, end_date)
        
        if not conversations:
            console.print("[bold yellow]No conversations found[/bold yellow]")
            return
        
        console.print(f"Extracted {len(conversations)} conversations")
        
        # Analyze conversations
        analyzer = ConversationAnalyzer()
        result = analyzer.analyze_conversations(conversations)
        
        # Sync to Notion
        notion_service = NotionService()
        created_pages = notion_service.sync_analysis_result(result, parent_page_id)
        
        # Log results
        total_pages = sum(len(pages) for pages in created_pages.values())
        console.print(f"[bold green]Created {total_pages} pages in Notion![/bold green]")
        for category, pages in created_pages.items():
            if pages:
                console.print(f"  {category.name}: {len(pages)} pages")
    
    except Exception as e:
        console.print(f"[bold red]Error syncing to Notion:[/bold red] {str(e)}")


@notion.command()
def test_notion() -> None:
    """Test Notion connection."""
    from devjourney.notion.service import NotionService
    
    console.print("[bold]Testing Notion connection...[/bold]")
    try:
        notion_service = NotionService()
        if notion_service.is_available():
            console.print("[bold green]Notion API is available![/bold green]")
        else:
            console.print("[bold red]Notion API is not available![/bold red]")
    except Exception as e:
        console.print(f"[bold red]Error testing Notion connection:[/bold red] {str(e)}")


def main() -> None:
    """Main entry point for the application."""
    try:
        cli()
    except Exception as e:
        logger.exception("An unexpected error occurred")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
