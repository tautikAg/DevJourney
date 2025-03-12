"""
Configuration settings for the DevJourney application.
"""
import os
import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field

# Default paths
HOME_DIR = Path.home()
CONFIG_DIR = HOME_DIR / ".devjourney"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
CACHE_DIR = CONFIG_DIR / "cache"
LOG_DIR = CONFIG_DIR / "logs"

# Ensure directories exist
CONFIG_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Default Cursor chat history path
DEFAULT_CURSOR_CHAT_PATH = HOME_DIR / ".cursor" / "chat_history"


class ExtractorConfig(BaseModel):
    """Configuration for data extractors."""
    claude_api_key: Optional[str] = Field(None, description="API key for Claude")
    claude_enabled: bool = Field(True, description="Whether Claude extraction is enabled")
    cursor_enabled: bool = Field(True, description="Whether Cursor extraction is enabled")
    cursor_chat_path: Path = Field(
        default=DEFAULT_CURSOR_CHAT_PATH, 
        description="Path to Cursor chat history"
    )
    extraction_frequency: int = Field(
        60, 
        description="Frequency of extraction in minutes"
    )
    max_history_days: int = Field(
        30, 
        description="Maximum number of days to extract history for"
    )


class NotionConfig(BaseModel):
    """Configuration for Notion integration."""
    api_key: Optional[str] = Field(None, description="Notion API key")
    enabled: bool = Field(True, description="Whether Notion integration is enabled")
    database_id: Optional[str] = Field(None, description="Notion database ID")
    sync_frequency: int = Field(
        120, 
        description="Frequency of Notion sync in minutes"
    )
    template_id: Optional[str] = Field(
        None, 
        description="Template ID for Notion database"
    )


class LLMConfig(BaseModel):
    """Configuration for LLM integration."""
    provider: str = Field(
        "ollama", 
        description="LLM provider (ollama, claude, openai)"
    )
    model: str = Field(
        "deepseek-r1", 
        description="Model to use for analysis"
    )
    api_key: Optional[str] = Field(None, description="API key for cloud LLM")
    temperature: float = Field(0.1, description="Temperature for LLM generation")
    max_tokens: int = Field(2000, description="Maximum tokens for LLM generation")
    fallback_providers: List[str] = Field(
        default=["claude", "openai"], 
        description="Fallback providers in order of preference"
    )


class UIConfig(BaseModel):
    """Configuration for the user interface."""
    theme: str = Field("system", description="UI theme (light, dark, system)")
    start_minimized: bool = Field(False, description="Start application minimized")
    show_notifications: bool = Field(True, description="Show desktop notifications")
    auto_start: bool = Field(False, description="Start application on system startup")


class CategoryConfig(BaseModel):
    """Configuration for content categories."""
    enabled_categories: List[str] = Field(
        default=["Problem/Solution", "Learning", "Code Reference", "Meeting Notes"],
        description="Enabled content categories"
    )
    custom_categories: List[str] = Field(
        default=[],
        description="Custom content categories"
    )
    technology_tags: List[str] = Field(
        default=["JavaScript", "Python", "AWS", "React", "Node.js", "Docker"],
        description="Technology tags"
    )
    custom_tags: List[str] = Field(
        default=[],
        description="Custom tags"
    )


class AppConfig(BaseModel):
    """Main application configuration."""
    extractors: ExtractorConfig = Field(default_factory=ExtractorConfig)
    notion: NotionConfig = Field(default_factory=NotionConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    categories: CategoryConfig = Field(default_factory=CategoryConfig)
    debug_mode: bool = Field(False, description="Enable debug mode")
    log_level: str = Field("INFO", description="Log level")


def load_config() -> AppConfig:
    """Load configuration from file or create default."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            config_data = yaml.safe_load(f)
            return AppConfig(**config_data)
    else:
        # Create default config
        config = AppConfig()
        save_config(config)
        return config


def save_config(config: AppConfig) -> None:
    """Save configuration to file."""
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(json.loads(config.model_dump_json()), f, default_flow_style=False)


# Global config instance
config = load_config()
