"""
Manager for conversation extractors.
"""
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Type

from devjourney.config.settings import config, CACHE_DIR
from devjourney.extractors.base import BaseExtractor
from devjourney.extractors.cursor import CursorExtractor
from devjourney.extractors.claude import ClaudeExtractor
from devjourney.models.conversation import Conversation

logger = logging.getLogger(__name__)

# Cache file for extracted conversations
CONVERSATIONS_CACHE_FILE = CACHE_DIR / "conversations.json"


class ExtractorManager:
    """Manager for conversation extractors."""
    
    def __init__(self):
        """Initialize the extractor manager."""
        self.extractors = []
        self.logger = logging.getLogger(__name__)
        
        # Initialize extractors based on configuration
        if config.extractors.cursor_enabled:
            self.extractors.append(CursorExtractor(
                chat_path=config.extractors.cursor_chat_path,
                max_history_days=config.extractors.max_history_days
            ))
        
        if config.extractors.claude_enabled:
            self.extractors.append(ClaudeExtractor(
                max_history_days=config.extractors.max_history_days
            ))
        
        self.logger.info(f"Initialized {len(self.extractors)} extractors")
    
    def extract_all(self, since: Optional[datetime] = None, force_refresh: bool = False) -> List[Conversation]:
        """
        Extract conversations from all available extractors.
        
        Args:
            since: Only extract conversations since this datetime
            force_refresh: Force refresh from sources instead of using cache
            
        Returns:
            List of extracted conversations
        """
        # Check if we can use cached conversations
        if not force_refresh and since:
            cached_conversations = self._load_cached_conversations(since)
            if cached_conversations:
                self.logger.info(f"Using {len(cached_conversations)} cached conversations")
                return cached_conversations
        
        # Extract from all available extractors
        all_conversations = []
        
        for extractor in self.extractors:
            if extractor.is_available():
                try:
                    conversations = extractor.extract(since)
                    self.logger.info(
                        f"Extracted {len(conversations)} conversations from {extractor.__class__.__name__}"
                    )
                    all_conversations.extend(conversations)
                except Exception as e:
                    self.logger.error(f"Error extracting from {extractor.__class__.__name__}: {str(e)}")
        
        # Cache the conversations
        self._cache_conversations(all_conversations)
        
        return all_conversations
    
    def get_available_extractors(self) -> List[BaseExtractor]:
        """
        Get all available extractors.
        
        Returns:
            List of available extractors
        """
        return [ext for ext in self.extractors if ext.is_available()]
    
    def _cache_conversations(self, conversations: List[Conversation]) -> None:
        """
        Cache conversations to disk.
        
        Args:
            conversations: List of conversations to cache
        """
        if not conversations:
            return
        
        try:
            # Convert conversations to dictionaries
            conv_dicts = [conv.to_dict() for conv in conversations]
            
            # Create cache directory if it doesn't exist
            CACHE_DIR.mkdir(exist_ok=True, parents=True)
            
            # Write to cache file
            with open(CONVERSATIONS_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(conv_dicts, f)
            
            self.logger.info(f"Cached {len(conversations)} conversations to {CONVERSATIONS_CACHE_FILE}")
        except Exception as e:
            self.logger.error(f"Error caching conversations: {str(e)}")
    
    def _load_cached_conversations(self, since: datetime) -> List[Conversation]:
        """
        Load cached conversations from disk.
        
        Args:
            since: Only load conversations since this datetime
            
        Returns:
            List of cached conversations
        """
        if not CONVERSATIONS_CACHE_FILE.exists():
            return []
        
        try:
            # Read from cache file
            with open(CONVERSATIONS_CACHE_FILE, 'r', encoding='utf-8') as f:
                conv_dicts = json.load(f)
            
            # Convert dictionaries to conversations
            conversations = []
            for conv_dict in conv_dicts:
                try:
                    conv = Conversation.from_dict(conv_dict)
                    # Check if the conversation is recent enough
                    if (conv.end_time or conv.start_time) >= since:
                        conversations.append(conv)
                except Exception as e:
                    self.logger.warning(f"Error parsing cached conversation: {str(e)}")
            
            self.logger.info(f"Loaded {len(conversations)} cached conversations from {CONVERSATIONS_CACHE_FILE}")
            return conversations
        except Exception as e:
            self.logger.error(f"Error loading cached conversations: {str(e)}")
            return []
    
    def clear_cache(self) -> bool:
        """
        Clear the conversation cache.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if CONVERSATIONS_CACHE_FILE.exists():
                CONVERSATIONS_CACHE_FILE.unlink()
                self.logger.info(f"Cleared conversation cache at {CONVERSATIONS_CACHE_FILE}")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing conversation cache: {str(e)}")
            return False


# Singleton instance
extractor_manager = ExtractorManager() 