"""
Configuration settings for DevJourney.
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "version": "1.0.0",
    "app": {
        "name": "DevJourney",
        "log_level": "INFO",
        "data_dir": "~/.devjourney",
    },
    "ui": {
        "theme": "dark",
        "start_minimized": False,
        "show_notifications": True,
    },
    "notion": {
        "enabled": False,
        "api_token": "",
        "parent_page_id": "",
        "sync_interval": 30,  # minutes
    },
    "extractors": {
        "enabled": True,
        "interval": 60,  # minutes
        "cursor": {
            "enabled": True,
            "history_path": "~/Library/Application Support/Cursor/chat_history.json",
        },
        "claude": {
            "enabled": False,
            "api_key": "",
        },
    },
    "analysis": {
        "enabled": True,
        "interval": 120,  # minutes
        "llm": {
            "provider": "ollama",
            "model": "llama3",
            "temperature": 0.7,
            "max_tokens": 1000,
        },
    },
    "storage": {
        "type": "sqlite",
        "path": "~/.devjourney/data.db",
    },
}


def get_config_path() -> Path:
    """Get the path to the config file."""
    # Get config directory from environment or use default
    config_dir = os.environ.get(
        "DEVJOURNEY_CONFIG_DIR", 
        os.path.expanduser(DEFAULT_CONFIG["app"]["data_dir"])
    )
    
    # Create directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)
    
    # Return path to config file
    return Path(config_dir) / "config.json"


def load_config() -> Dict[str, Any]:
    """Load configuration from file or create default if not exists."""
    config_path = get_config_path()
    
    # If config file exists, load it
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                loaded_config = json.load(f)
            
            logger.info(f"Loaded configuration from {config_path}")
            
            # Merge with default config to ensure all keys exist
            return _merge_configs(DEFAULT_CONFIG, loaded_config)
            
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {str(e)}")
            logger.info("Using default configuration")
            return DEFAULT_CONFIG
    
    # If config file doesn't exist, create it with default values
    try:
        with open(config_path, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        
        logger.info(f"Created default configuration at {config_path}")
        return DEFAULT_CONFIG
        
    except Exception as e:
        logger.error(f"Error creating config at {config_path}: {str(e)}")
        logger.info("Using default configuration in memory")
        return DEFAULT_CONFIG


def save_config(config_data: Dict[str, Any]) -> bool:
    """Save configuration to file.
    
    Args:
        config_data: Configuration data to save
        
    Returns:
        True if successful, False otherwise
    """
    config_path = get_config_path()
    
    try:
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)
        
        logger.info(f"Saved configuration to {config_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving config to {config_path}: {str(e)}")
        return False


def _merge_configs(default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge user config with default config.
    
    This ensures all keys from default exist in the result,
    while preserving user-specified values.
    
    Args:
        default: Default configuration
        user: User configuration
        
    Returns:
        Merged configuration
    """
    result = default.copy()
    
    for key, value in user.items():
        # If both values are dicts, merge them recursively
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_configs(result[key], value)
        # Otherwise, use the user value
        else:
            result[key] = value
    
    return result


def update_config(section: str, key: str, value: Any) -> bool:
    """Update a specific configuration value.
    
    Args:
        section: Configuration section (e.g., "notion")
        key: Configuration key within section
        value: New value
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load current config
        current_config = config.copy()
        
        # Update value
        if section in current_config:
            current_config[section][key] = value
        else:
            current_config[section] = {key: value}
        
        # Save updated config
        if save_config(current_config):
            # Update in-memory config
            config.update(current_config)
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error updating config {section}.{key}: {str(e)}")
        return False


# Load configuration on module import
config = load_config()
