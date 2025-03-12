"""
Factory for creating extractors.
"""
from typing import Optional, Dict, Type

from devjourney.extractors.base import BaseExtractor
from devjourney.extractors.cursor import CursorExtractor
from devjourney.extractors.claude import ClaudeExtractor
from devjourney.config.settings import config

# Registry of available extractors
EXTRACTORS: Dict[str, Type[BaseExtractor]] = {
    "cursor": CursorExtractor,
    "claude": ClaudeExtractor,
}


def create_extractor(source_type: str) -> Optional[BaseExtractor]:
    """
    Create an extractor for the specified source type.
    
    Args:
        source_type: Type of source to extract from
        
    Returns:
        Extractor instance or None if source type is not supported
    """
    extractor_class = EXTRACTORS.get(source_type.lower())
    
    if not extractor_class:
        return None
    
    # Create the extractor with configuration from settings
    if source_type.lower() == "cursor":
        return extractor_class(
            chat_path=config.extractors.cursor_chat_path,
            max_history_days=config.extractors.max_history_days
        )
    elif source_type.lower() == "claude":
        return extractor_class(
            max_history_days=config.extractors.max_history_days
        )
    
    # Default case
    return extractor_class()


def register_extractor(source_type: str, extractor_class: Type[BaseExtractor]) -> None:
    """
    Register a new extractor type.
    
    Args:
        source_type: Type of source to extract from
        extractor_class: Extractor class to register
    """
    EXTRACTORS[source_type.lower()] = extractor_class 