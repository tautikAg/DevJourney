"""
Base extractor interface for conversation data sources.
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from devjourney.models.conversation import Conversation

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Base class for all conversation extractors."""
    
    def __init__(self, max_history_days: int = 30):
        """
        Initialize the extractor.
        
        Args:
            max_history_days: Maximum number of days to extract history for
        """
        self.max_history_days = max_history_days
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def extract(self, since: Optional[datetime] = None) -> List[Conversation]:
        """
        Extract conversations from the source.
        
        Args:
            since: Only extract conversations since this datetime
            
        Returns:
            List of extracted conversations
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the extractor is available.
        
        Returns:
            True if the extractor is available, False otherwise
        """
        pass
    
    def get_default_since_date(self) -> datetime:
        """
        Get the default date to extract conversations since.
        
        Returns:
            Datetime object representing the default since date
        """
        return datetime.now() - timedelta(days=self.max_history_days)
    
    def _log_extraction_stats(self, conversations: List[Conversation]) -> None:
        """
        Log statistics about extracted conversations.
        
        Args:
            conversations: List of extracted conversations
        """
        if not conversations:
            self.logger.info("No conversations extracted")
            return
        
        total_messages = sum(conv.message_count for conv in conversations)
        earliest = min(conv.start_time for conv in conversations)
        latest = max(conv.end_time or conv.start_time for conv in conversations)
        
        self.logger.info(
            f"Extracted {len(conversations)} conversations with {total_messages} messages "
            f"from {earliest.isoformat()} to {latest.isoformat()}"
        ) 