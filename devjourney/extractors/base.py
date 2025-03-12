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
    
    def extract_conversations(self, start_date: datetime, end_date: Optional[datetime] = None) -> List[Conversation]:
        """
        Extract conversations between start_date and end_date.
        
        Args:
            start_date: Start date for extraction
            end_date: End date for extraction (defaults to now)
            
        Returns:
            List of extracted conversations
        """
        self.logger.info(f"Extracting conversations from {start_date.isoformat()} to {end_date.isoformat() if end_date else 'now'}")
        conversations = self.extract(since=start_date)
        
        # Filter by end date if provided
        if end_date:
            conversations = [
                conv for conv in conversations 
                if conv.start_time <= end_date
            ]
        
        self._log_extraction_stats(conversations)
        return conversations
    
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
        
    def set_file_path(self, file_path: str) -> None:
        """
        Set the file path for file-based extractors.
        
        Args:
            file_path: Path to the file containing conversations
        """
        # This is a default implementation that does nothing
        # Subclasses should override this method if they support file-based extraction
        self.logger.warning(f"File-based extraction not supported by {self.__class__.__name__}") 