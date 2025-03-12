"""
Command-line interface package for DevJourney.
"""
from devjourney.cli.notion_commands import setup_notion_parser, handle_notion_command

__all__ = ["setup_notion_parser", "handle_notion_command"] 