#!/usr/bin/env python3
"""
DevJourney - A personal progress tracking system.

This module serves as the main entry point for the DevJourney application.
"""
import os
import sys
import logging
import click
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler

from devjourney.config.settings import config, CONFIG_DIR, LOG_DIR

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
def cli():
    """DevJourney - Track your development progress from AI conversations."""
    pass


@cli.command()
def setup():
    """Run the setup wizard to configure DevJourney."""
    from devjourney.ui.setup_wizard import run_setup_wizard
    console.print("[bold green]Starting DevJourney setup wizard...[/bold green]")
    run_setup_wizard()


@cli.command()
@click.option("--headless", is_flag=True, help="Run in headless mode without UI")
def start(headless):
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
def status():
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
def sync(force):
    """Manually trigger a sync with Notion."""
    from devjourney.notion.sync import sync_to_notion
    
    console.print("[bold]Manually triggering Notion sync...[/bold]")
    result = sync_to_notion(force=force)
    
    if result["success"]:
        console.print(f"[bold green]Sync completed successfully![/bold green]")
        console.print(f"Items synced: {result['items_synced']}")
    else:
        console.print(f"[bold red]Sync failed![/bold red]")
        console.print(f"Error: {result['error']}")


@cli.command()
@click.option("--days", default=7, help="Number of days to analyze")
def analyze(days):
    """Analyze recent conversations without syncing to Notion."""
    from devjourney.analyzers.analyzer import analyze_recent_conversations
    
    console.print(f"[bold]Analyzing conversations from the last {days} days...[/bold]")
    result = analyze_recent_conversations(days=days)
    
    console.print(f"[bold green]Analysis complete![/bold green]")
    console.print(f"Conversations analyzed: {result['conversations_analyzed']}")
    console.print(f"Problems identified: {result['problems_identified']}")
    console.print(f"Learnings extracted: {result['learnings_extracted']}")
    console.print(f"Code references found: {result['code_references']}")


def main():
    """Main entry point for the application."""
    try:
        cli()
    except Exception as e:
        logger.exception("An unexpected error occurred")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
