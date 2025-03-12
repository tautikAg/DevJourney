"""
Setup wizard for DevJourney.
"""
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from rich.console import Console
from rich.prompt import Prompt, Confirm

from devjourney.config.settings import config, save_config
from devjourney.utils.credentials import (
    store_notion_token, get_notion_token,
    store_claude_api_key, get_claude_api_key,
    store_openai_api_key, get_openai_api_key
)

logger = logging.getLogger(__name__)
console = Console()


def run_setup_wizard() -> None:
    """Run the setup wizard to configure DevJourney."""
    console.print("[bold]Welcome to DevJourney Setup Wizard![/bold]")
    console.print("This wizard will help you configure DevJourney for your needs.")
    
    # Configure Notion integration
    setup_notion()
    
    # Configure extractors
    setup_extractors()
    
    # Configure LLM
    setup_llm()
    
    # Configure UI
    setup_ui()
    
    # Save configuration
    save_config(config)
    
    console.print("[bold green]Setup complete![/bold green]")
    console.print("You can now start using DevJourney.")


def setup_notion() -> None:
    """Configure Notion integration."""
    console.print("\n[bold]Notion Integration Setup[/bold]")
    
    # Check if Notion integration is enabled
    config.notion.enabled = Confirm.ask(
        "Enable Notion integration?",
        default=config.notion.enabled
    )
    
    if not config.notion.enabled:
        console.print("[yellow]Notion integration disabled.[/yellow]")
        return
    
    # Get Notion API key
    notion_token = get_notion_token()
    if notion_token:
        console.print("[green]Notion token already configured.[/green]")
        if Confirm.ask("Do you want to update your Notion token?", default=False):
            notion_token = Prompt.ask(
                "Enter your Notion API token",
                password=True
            )
            store_notion_token(notion_token)
    else:
        console.print("You need a Notion API token to use the Notion integration.")
        console.print("You can create one at https://www.notion.so/my-integrations")
        notion_token = Prompt.ask(
            "Enter your Notion API token",
            password=True
        )
        store_notion_token(notion_token)
    
    # Get parent page ID
    config.notion.parent_page_id = Prompt.ask(
        "Enter your Notion parent page ID",
        default=config.notion.parent_page_id or ""
    )
    
    # Configure sync frequency
    sync_options = ["hourly", "daily", "weekly"]
    sync_index = sync_options.index(config.notion.sync_frequency) if config.notion.sync_frequency in sync_options else 1
    config.notion.sync_frequency = Prompt.ask(
        "Select sync frequency",
        choices=sync_options,
        default=sync_options[sync_index]
    )
    
    console.print("[green]Notion integration configured.[/green]")


def setup_extractors() -> None:
    """Configure extractors."""
    console.print("\n[bold]Extractors Setup[/bold]")
    
    # Configure Cursor extractor
    config.extractors.cursor_enabled = Confirm.ask(
        "Enable Cursor chat history extraction?",
        default=config.extractors.cursor_enabled
    )
    
    if config.extractors.cursor_enabled:
        cursor_path = Prompt.ask(
            "Enter path to Cursor chat history",
            default=str(config.extractors.cursor_chat_path)
        )
        config.extractors.cursor_chat_path = Path(cursor_path)
    
    # Configure Claude extractor
    config.extractors.claude_enabled = Confirm.ask(
        "Enable Claude API extraction?",
        default=config.extractors.claude_enabled
    )
    
    if config.extractors.claude_enabled:
        claude_api_key = get_claude_api_key()
        if claude_api_key:
            console.print("[green]Claude API key already configured.[/green]")
            if Confirm.ask("Do you want to update your Claude API key?", default=False):
                claude_api_key = Prompt.ask(
                    "Enter your Claude API key",
                    password=True
                )
                store_claude_api_key(claude_api_key)
        else:
            console.print("You need a Claude API key to use the Claude extractor.")
            claude_api_key = Prompt.ask(
                "Enter your Claude API key",
                password=True
            )
            store_claude_api_key(claude_api_key)
    
    # Configure extraction frequency
    config.extractors.extraction_frequency = int(Prompt.ask(
        "Enter extraction frequency in minutes",
        default=str(config.extractors.extraction_frequency)
    ))
    
    # Configure max history days
    config.extractors.max_history_days = int(Prompt.ask(
        "Enter maximum number of days to extract history for",
        default=str(config.extractors.max_history_days)
    ))
    
    console.print("[green]Extractors configured.[/green]")


def setup_llm() -> None:
    """Configure LLM integration."""
    console.print("\n[bold]LLM Setup[/bold]")
    
    # Configure LLM provider
    llm_options = ["ollama", "claude", "openai"]
    llm_index = llm_options.index(config.llm.provider) if config.llm.provider in llm_options else 0
    config.llm.provider = Prompt.ask(
        "Select LLM provider",
        choices=llm_options,
        default=llm_options[llm_index]
    )
    
    # Configure model
    if config.llm.provider == "ollama":
        config.llm.model = Prompt.ask(
            "Enter Ollama model name",
            default=config.llm.model or "deepseek-r1"
        )
    elif config.llm.provider == "claude":
        config.llm.model = Prompt.ask(
            "Enter Claude model name",
            default=config.llm.model or "claude-3-opus-20240229"
        )
        
        # Check Claude API key
        claude_api_key = get_claude_api_key()
        if not claude_api_key:
            console.print("You need a Claude API key to use Claude as LLM provider.")
            claude_api_key = Prompt.ask(
                "Enter your Claude API key",
                password=True
            )
            store_claude_api_key(claude_api_key)
    elif config.llm.provider == "openai":
        config.llm.model = Prompt.ask(
            "Enter OpenAI model name",
            default=config.llm.model or "gpt-4-turbo"
        )
        
        # Check OpenAI API key
        openai_api_key = get_openai_api_key()
        if not openai_api_key:
            console.print("You need an OpenAI API key to use OpenAI as LLM provider.")
            openai_api_key = Prompt.ask(
                "Enter your OpenAI API key",
                password=True
            )
            store_openai_api_key(openai_api_key)
    
    # Configure temperature
    config.llm.temperature = float(Prompt.ask(
        "Enter temperature for LLM generation",
        default=str(config.llm.temperature)
    ))
    
    # Configure max tokens
    config.llm.max_tokens = int(Prompt.ask(
        "Enter maximum tokens for LLM generation",
        default=str(config.llm.max_tokens)
    ))
    
    console.print("[green]LLM configured.[/green]")


def setup_ui() -> None:
    """Configure UI."""
    console.print("\n[bold]UI Setup[/bold]")
    
    # Configure theme
    theme_options = ["light", "dark", "system"]
    theme_index = theme_options.index(config.ui.theme) if config.ui.theme in theme_options else 2
    config.ui.theme = Prompt.ask(
        "Select UI theme",
        choices=theme_options,
        default=theme_options[theme_index]
    )
    
    # Configure start minimized
    config.ui.start_minimized = Confirm.ask(
        "Start application minimized?",
        default=config.ui.start_minimized
    )
    
    # Configure show notifications
    config.ui.show_notifications = Confirm.ask(
        "Show desktop notifications?",
        default=config.ui.show_notifications
    )
    
    # Configure auto start
    config.ui.auto_start = Confirm.ask(
        "Start application on system startup?",
        default=config.ui.auto_start
    )
    
    console.print("[green]UI configured.[/green]") 