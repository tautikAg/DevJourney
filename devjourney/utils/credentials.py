"""
Utilities for secure credential storage.
"""
import logging
import keyring
from typing import Optional

logger = logging.getLogger(__name__)

# Service names for different credentials
NOTION_SERVICE = "devjourney_notion"
CLAUDE_SERVICE = "devjourney_claude"
OPENAI_SERVICE = "devjourney_openai"


def store_credential(service: str, username: str, credential: str) -> bool:
    """
    Store a credential securely in the system keyring.
    
    Args:
        service: Service identifier
        username: Username or identifier for the credential
        credential: The credential to store (e.g., API key)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        keyring.set_password(service, username, credential)
        logger.info(f"Stored credential for {service}")
        return True
    except Exception as e:
        logger.error(f"Failed to store credential for {service}: {str(e)}")
        return False


def get_credential(service: str, username: str) -> Optional[str]:
    """
    Retrieve a credential from the system keyring.
    
    Args:
        service: Service identifier
        username: Username or identifier for the credential
        
    Returns:
        Optional[str]: The credential if found, None otherwise
    """
    try:
        credential = keyring.get_password(service, username)
        return credential
    except Exception as e:
        logger.error(f"Failed to retrieve credential for {service}: {str(e)}")
        return None


def delete_credential(service: str, username: str) -> bool:
    """
    Delete a credential from the system keyring.
    
    Args:
        service: Service identifier
        username: Username or identifier for the credential
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        keyring.delete_password(service, username)
        logger.info(f"Deleted credential for {service}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete credential for {service}: {str(e)}")
        return False


# Convenience functions for specific services

def store_notion_token(token: str) -> bool:
    """Store Notion API token."""
    return store_credential(NOTION_SERVICE, "token", token)


def get_notion_token() -> Optional[str]:
    """Get Notion API token."""
    return get_credential(NOTION_SERVICE, "token")


def store_claude_api_key(api_key: str) -> bool:
    """Store Claude API key."""
    return store_credential(CLAUDE_SERVICE, "api_key", api_key)


def get_claude_api_key() -> Optional[str]:
    """Get Claude API key."""
    return get_credential(CLAUDE_SERVICE, "api_key")


def store_openai_api_key(api_key: str) -> bool:
    """Store OpenAI API key."""
    return store_credential(OPENAI_SERVICE, "api_key", api_key)


def get_openai_api_key() -> Optional[str]:
    """Get OpenAI API key."""
    return get_credential(OPENAI_SERVICE, "api_key") 