"""
Main application UI for DevJourney.
"""
import logging
import sys
import time
from typing import Optional, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout

from devjourney.config.settings import config
from devjourney.utils.service_manager import check_status, start_services, stop_services

logger = logging.getLogger(__name__)
console = Console()


def start_app() -> None:
    """Start the DevJourney application UI."""
    try:
        # Start background services
        start_services()
        
        # Show UI
        show_ui()
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down DevJourney...[/yellow]")
        stop_services()
        sys.exit(0)
    except Exception as e:
        logger.exception("Error starting DevJourney application")
        console.print(f"[bold red]Error starting DevJourney application:[/bold red] {str(e)}")
        stop_services()
        sys.exit(1)


def show_ui() -> None:
    """Show the DevJourney UI."""
    console.print("[bold green]DevJourney is running![/bold green]")
    console.print("Press Ctrl+C to exit.")
    
    try:
        with Live(refresh_per_second=1) as live:
            while True:
                # Create layout
                layout = create_layout()
                
                # Update live display
                live.update(layout)
                
                # Sleep for a bit
                time.sleep(5)
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down DevJourney...[/yellow]")
        stop_services()
        sys.exit(0)


def create_layout() -> Layout:
    """Create the UI layout."""
    layout = Layout()
    
    # Create header
    header = Panel(
        "[bold]DevJourney[/bold] - Personal Progress Tracking System",
        style="blue"
    )
    
    # Create status table
    status_table = create_status_table()
    
    # Create footer
    footer = Panel(
        "Press Ctrl+C to exit",
        style="dim"
    )
    
    # Set up layout
    layout.split(
        Layout(header, size=3),
        Layout(status_table),
        Layout(footer, size=3)
    )
    
    return layout


def create_status_table() -> Table:
    """Create a table showing the status of services."""
    status_info = check_status()
    
    table = Table(title="Service Status")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Details", style="green")
    
    for service, status in status_info.items():
        status_text = "[green]Running[/green]" if status["running"] else "[red]Stopped[/red]"
        details = status.get("details", "")
        table.add_row(service, status_text, details)
    
    return table 