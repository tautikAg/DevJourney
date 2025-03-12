"""
Extractor for Claude API conversations.
"""
import logging
import uuid
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import requests
from requests.exceptions import RequestException

from devjourney.config.settings import config
from devjourney.extractors.base import BaseExtractor
from devjourney.models.conversation import (
    Conversation, Message, MessageContent, MessageRole, ConversationSource
)
from devjourney.utils.credentials import get_claude_api_key

logger = logging.getLogger(__name__)

# Claude API endpoints
API_BASE_URL = "https://api.anthropic.com/v1"
CONVERSATIONS_ENDPOINT = f"{API_BASE_URL}/conversations"
MESSAGES_ENDPOINT = f"{API_BASE_URL}/messages"


class ClaudeExtractor(BaseExtractor):
    """Extractor for Claude API conversations."""
    
    def __init__(self, api_key: Optional[str] = None, max_history_days: int = 30):
        """
        Initialize the Claude extractor.
        
        Args:
            api_key: Claude API key (if None, will try to get from credentials)
            max_history_days: Maximum number of days to extract history for
        """
        super().__init__(max_history_days)
        self.api_key = api_key or get_claude_api_key()
        self.logger.info("Initialized Claude extractor")
    
    def is_available(self) -> bool:
        """
        Check if Claude API is available.
        
        Returns:
            True if Claude API is available, False otherwise
        """
        if not self.api_key:
            self.logger.warning("Claude API key not available")
            return False
        
        try:
            # Make a simple API call to check if the API is available
            response = self._make_api_request(CONVERSATIONS_ENDPOINT, params={"limit": 1})
            return response.status_code == 200
        except Exception as e:
            self.logger.warning(f"Claude API not available: {str(e)}")
            return False
    
    def extract(self, since: Optional[datetime] = None) -> List[Conversation]:
        """
        Extract conversations from Claude API.
        
        Args:
            since: Only extract conversations since this datetime
            
        Returns:
            List of extracted conversations
        """
        if not self.is_available():
            self.logger.warning("Claude API not available")
            return []
        
        since = since or self.get_default_since_date()
        self.logger.info(f"Extracting Claude conversations since {since.isoformat()}")
        
        # Get conversation list
        conversations = []
        page_token = None
        
        while True:
            try:
                # Get a page of conversations
                params = {"limit": 50}
                if page_token:
                    params["page_token"] = page_token
                
                response = self._make_api_request(CONVERSATIONS_ENDPOINT, params=params)
                data = response.json()
                
                # Process conversations
                for conv_data in data.get("conversations", []):
                    # Check if the conversation is recent enough
                    conv_time = self._parse_timestamp(conv_data.get("created_at"))
                    if conv_time and conv_time < since:
                        continue
                    
                    # Get conversation details and messages
                    conversation = self._get_conversation_details(conv_data.get("id"))
                    if conversation:
                        conversations.append(conversation)
                
                # Check if there are more pages
                page_token = data.get("page_token")
                if not page_token:
                    break
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error extracting Claude conversations: {str(e)}")
                break
        
        self._log_extraction_stats(conversations)
        return conversations
    
    def _get_conversation_details(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get details for a specific conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Conversation object or None if retrieval failed
        """
        try:
            # Get conversation metadata
            response = self._make_api_request(f"{CONVERSATIONS_ENDPOINT}/{conversation_id}")
            conv_data = response.json()
            
            # Get conversation messages
            messages_response = self._make_api_request(
                f"{CONVERSATIONS_ENDPOINT}/{conversation_id}/messages",
                params={"limit": 100}
            )
            messages_data = messages_response.json()
            
            # Parse messages
            messages = []
            for msg_data in messages_data.get("messages", []):
                message = self._parse_message(msg_data)
                if message:
                    messages.append(message)
            
            if not messages:
                return None
            
            # Sort messages by timestamp
            messages.sort(key=lambda msg: msg.timestamp)
            
            # Determine conversation timestamps
            start_time = messages[0].timestamp
            end_time = messages[-1].timestamp
            
            # Get title
            title = conv_data.get("title", f"Claude conversation {conversation_id[:8]}")
            
            return Conversation(
                id=conversation_id,
                title=title,
                source=ConversationSource.CLAUDE,
                messages=messages,
                start_time=start_time,
                end_time=end_time,
                metadata={
                    "model": conv_data.get("model"),
                    "created_at": conv_data.get("created_at"),
                    "updated_at": conv_data.get("updated_at"),
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error getting conversation details for {conversation_id}: {str(e)}")
            return None
    
    def _parse_message(self, msg_data: Dict[str, Any]) -> Optional[Message]:
        """
        Parse a message from Claude API.
        
        Args:
            msg_data: Message data from Claude API
            
        Returns:
            Parsed message or None if parsing failed
        """
        # Extract message role
        role_str = msg_data.get("role", "").lower()
        if role_str == "user":
            role = MessageRole.USER
        elif role_str == "assistant":
            role = MessageRole.ASSISTANT
        else:
            self.logger.warning(f"Unknown message role: {role_str}")
            return None
        
        # Extract message content
        content = msg_data.get("content", [])
        if not content:
            return None
        
        # Parse timestamp
        timestamp = self._parse_timestamp(msg_data.get("created_at"))
        if not timestamp:
            timestamp = datetime.now()
        
        # Parse content blocks
        content_blocks = []
        for block in content:
            block_type = block.get("type")
            if block_type == "text":
                content_blocks.append(MessageContent(
                    text=block.get("text", ""),
                    is_code=False
                ))
            elif block_type == "code":
                content_blocks.append(MessageContent(
                    text=block.get("text", ""),
                    language=block.get("language"),
                    is_code=True
                ))
        
        if not content_blocks:
            return None
        
        return Message(
            id=msg_data.get("id", str(uuid.uuid4())),
            role=role,
            content=content_blocks,
            timestamp=timestamp,
            metadata={k: v for k, v in msg_data.items() if k not in ("id", "role", "content", "created_at")}
        )
    
    def _make_api_request(self, endpoint: str, method: str = "GET", params: Dict[str, Any] = None, 
                         data: Dict[str, Any] = None, max_retries: int = 3) -> requests.Response:
        """
        Make an API request to Claude API with retry logic.
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            params: Query parameters
            data: Request body
            max_retries: Maximum number of retries
            
        Returns:
            Response object
            
        Raises:
            RequestException: If the request fails after all retries
        """
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=endpoint,
                    headers=headers,
                    params=params,
                    json=data,
                    timeout=30
                )
                
                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("retry-after", 1))
                    self.logger.warning(f"Rate limited, retrying after {retry_after} seconds")
                    time.sleep(retry_after)
                    continue
                
                # Check for server errors
                if response.status_code >= 500:
                    self.logger.warning(f"Server error {response.status_code}, retrying")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                
                # Check for client errors
                if response.status_code >= 400 and response.status_code != 429:
                    error_msg = f"API error: {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg = f"{error_msg} - {error_data.get('error', {}).get('message', '')}"
                    except:
                        pass
                    raise RequestException(error_msg)
                
                return response
                
            except RequestException as e:
                if attempt == max_retries - 1:
                    raise
                self.logger.warning(f"Request failed, retrying: {str(e)}")
                time.sleep(2 ** attempt)  # Exponential backoff
        
        raise RequestException("Max retries exceeded")
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """
        Parse a timestamp string from Claude API.
        
        Args:
            timestamp_str: Timestamp string in ISO format
            
        Returns:
            Parsed datetime or None if parsing failed
        """
        if not timestamp_str:
            return None
        
        try:
            # Claude API uses ISO format with 'Z' for UTC
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            self.logger.warning(f"Failed to parse timestamp: {timestamp_str}")
            return None 