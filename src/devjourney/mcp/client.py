"""
MCP client for Claude integration.

This module implements a client for the Model Context Protocol (MCP)
to interact with Claude desktop and extract conversation history.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx
from mcp.client.session import ClientSession as Client
from mcp.types import (
    Resource,
    Tool,
)

from devjourney.database import get_db
from devjourney.models import (
    ContentBlock,
    ContentType,
    Conversation,
    ConversationSource,
    Message,
    MessageRole,
)

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Exception raised for MCP client errors."""
    pass


# Define our own TextContent and EmbeddedResource types since they're not available in mcp.types
class TextContent:
    """Text content from a tool call."""
    def __init__(self, text: str, type: str = "text"):
        self.text = text
        self.type = type


class EmbeddedResource:
    """Embedded resource from a tool call."""
    def __init__(self, resource_id: str, mime_type: str):
        self.resource_id = resource_id
        self.mime_type = mime_type


class ClaudeMCPClient:
    """Client for interacting with Claude via MCP."""

    def __init__(self, host: str = "localhost", port: int = 8000):
        """Initialize the Claude MCP client.
        
        Args:
            host: The MCP server host.
            port: The MCP server port.
        """
        self.host = host
        self.port = port
        self.client: Optional[httpx.AsyncClient] = None
        self.db = get_db()
        self.config = self.db.get_config()

    async def connect(self) -> None:
        """Connect to the MCP server."""
        try:
            # Create a direct httpx client instead of using the MCP client
            # since the MCP client API might have changed
            self.client = httpx.AsyncClient(base_url=f"http://{self.host}:{self.port}")
            logger.info(f"Connected to MCP server at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise MCPClientError(f"Failed to connect to MCP server: {e}")

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self.client:
            await self.client.aclose()
            logger.info("Disconnected from MCP server")

    async def get_available_tools(self) -> List[Tool]:
        """Get available tools from the MCP server.
        
        Returns:
            A list of available tools.
        """
        if not self.client:
            await self.connect()
        
        try:
            response = await self.client.get("/tools")
            tools = response.json()
            logger.debug(f"Available tools: {tools}")
            return tools
        except Exception as e:
            logger.error(f"Failed to get available tools: {e}")
            raise MCPClientError(f"Failed to get available tools: {e}")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server.
        
        Args:
            tool_name: The name of the tool to call.
            arguments: The arguments to pass to the tool.
            
        Returns:
            The result of the tool call.
        """
        if not self.client:
            await self.connect()
        
        try:
            response = await self.client.post("/tools", json={"name": tool_name, "arguments": arguments})
            result = response.json()
            logger.debug(f"Tool call result: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to call tool: {e}")
            raise MCPClientError(f"Failed to call tool: {e}")

    async def get_conversation_history(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get conversation history from the MCP server.
        
        Args:
            since: Only get conversations since this time.
            
        Returns:
            A list of conversations.
        """
        if not self.client:
            await self.connect()
        
        try:
            # Construct the query parameters
            params = {}
            if since:
                params["since"] = since.isoformat()
            
            # Call the conversations endpoint
            response = await self.client.get("/conversations", params=params)
            conversations = response.json()
            
            logger.info(f"Got {len(conversations)} conversations from MCP server")
            return conversations
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            raise MCPClientError(f"Failed to get conversation history: {e}")

    def _mock_conversation_history(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Mock implementation of conversation history.
        
        Args:
            since: Only get conversations since this time.
            
        Returns:
            A list of mock conversations.
        """
        # This is a mock implementation for development purposes
        now = datetime.utcnow()
        
        mock_conversations = [
            {
                "id": "conv_123456",
                "title": "Python Error Handling",
                "start_time": (now.replace(hour=now.hour - 2)).isoformat(),
                "end_time": (now.replace(hour=now.hour - 1)).isoformat(),
                "messages": [
                    {
                        "id": "msg_1",
                        "role": "user",
                        "timestamp": (now.replace(hour=now.hour - 2)).isoformat(),
                        "content": [
                            {
                                "type": "text",
                                "content": "What's the best way to handle errors in Python?"
                            }
                        ]
                    },
                    {
                        "id": "msg_2",
                        "role": "assistant",
                        "timestamp": (now.replace(hour=now.hour - 2, minute=now.minute + 1)).isoformat(),
                        "content": [
                            {
                                "type": "text",
                                "content": "In Python, there are several approaches to error handling. The most common is using try/except blocks."
                            },
                            {
                                "type": "code",
                                "language": "python",
                                "content": "try:\n    # Code that might raise an exception\n    result = risky_operation()\nexcept Exception as e:\n    # Handle the exception\n    print(f\"An error occurred: {e}\")\nelse:\n    # Code to run if no exception occurred\n    print(\"Operation succeeded!\")\nfinally:\n    # Code that runs regardless of whether an exception occurred\n    print(\"Cleanup code\")"
                            }
                        ]
                    }
                ]
            },
            {
                "id": "conv_789012",
                "title": "React Component Design",
                "start_time": (now.replace(hour=now.hour - 1)).isoformat(),
                "end_time": now.isoformat(),
                "messages": [
                    {
                        "id": "msg_3",
                        "role": "user",
                        "timestamp": (now.replace(hour=now.hour - 1)).isoformat(),
                        "content": [
                            {
                                "type": "text",
                                "content": "How should I structure a React component for a todo list?"
                            }
                        ]
                    },
                    {
                        "id": "msg_4",
                        "role": "assistant",
                        "timestamp": (now.replace(hour=now.hour - 1, minute=now.minute + 2)).isoformat(),
                        "content": [
                            {
                                "type": "text",
                                "content": "Here's a good structure for a React Todo List component:"
                            },
                            {
                                "type": "code",
                                "language": "jsx",
                                "content": "import React, { useState } from 'react';\n\nfunction TodoList() {\n  const [todos, setTodos] = useState([]);\n  const [input, setInput] = useState('');\n\n  const addTodo = () => {\n    if (input.trim() !== '') {\n      setTodos([...todos, { id: Date.now(), text: input, completed: false }]);\n      setInput('');\n    }\n  };\n\n  const toggleTodo = (id) => {\n    setTodos(todos.map(todo => \n      todo.id === id ? { ...todo, completed: !todo.completed } : todo\n    ));\n  };\n\n  return (\n    <div>\n      <h1>Todo List</h1>\n      <div>\n        <input \
            value={input} \
            onChange={(e) => setInput(e.target.value)} \
            placeholder=\"Add a todo\"\
          />\
          <button onClick={addTodo}>Add</button>\
        </div>\
        <ul>\
          {todos.map(todo => (\
            <li \
              key={todo.id} \
              style={{ textDecoration: todo.completed ? 'line-through' : 'none' }}\
              onClick={() => toggleTodo(todo.id)}\
            >\
              {todo.text}\
            </li>\
          ))}\
        </ul>\
      </div>\
    );\
  }\
\nexport default TodoList;"
                            }
                        ]
                    }
                ]
            }
        ]
        
        # Filter by time if needed
        if since:
            mock_conversations = [
                conv for conv in mock_conversations 
                if datetime.fromisoformat(conv["start_time"]) >= since
            ]
        
        return mock_conversations

    async def process_conversation_history(self, conversations: List[Dict[str, Any]]) -> List[Conversation]:
        """Process conversation history and store in the database.
        
        Args:
            conversations: A list of conversations from Claude.
            
        Returns:
            A list of processed Conversation objects.
        """
        processed_conversations = []
        
        for conv_data in conversations:
            # Check if conversation already exists in the database
            existing_convs = self.db.get_items(
                Conversation, 
                source=ConversationSource.CLAUDE, 
                source_id=conv_data["id"]
            )
            
            if existing_convs:
                logger.debug(f"Conversation {conv_data['id']} already exists, skipping")
                processed_conversations.append(existing_convs[0])
                continue
            
            # Create a new conversation
            start_time = datetime.fromisoformat(conv_data["start_time"])
            end_time = datetime.fromisoformat(conv_data["end_time"]) if "end_time" in conv_data else None
            
            conversation = Conversation(
                source=ConversationSource.CLAUDE,
                source_id=conv_data["id"],
                title=conv_data.get("title", "Untitled Conversation"),
                start_time=start_time,
                end_time=end_time,
                metadata={}
            )
            
            # Add the conversation to the database
            conversation = self.db.add_item(conversation)
            
            # Process messages
            messages = []
            for msg_data in conv_data.get("messages", []):
                role_str = msg_data.get("role", "user").lower()
                role = MessageRole.USER if role_str == "user" else MessageRole.ASSISTANT if role_str == "assistant" else MessageRole.SYSTEM
                
                timestamp = datetime.fromisoformat(msg_data["timestamp"])
                
                # Process content blocks
                content_blocks = []
                for block in msg_data.get("content", []):
                    block_type_str = block.get("type", "text").lower()
                    block_type = ContentType.TEXT
                    
                    if block_type_str == "code":
                        block_type = ContentType.CODE
                    elif block_type_str == "image":
                        block_type = ContentType.IMAGE
                    elif block_type_str == "file":
                        block_type = ContentType.FILE
                    
                    content_block = {
                        "type": block_type,
                        "content": block.get("content", ""),
                        "language": block.get("language") if block_type == ContentType.CODE else None,
                        "metadata": block.get("metadata", {})
                    }
                    
                    content_blocks.append(content_block)
                
                message = Message(
                    conversation_id=conversation.id,
                    role=role,
                    timestamp=timestamp,
                    content_blocks=content_blocks
                )
                
                messages.append(message)
            
            # Add messages to the database
            if messages:
                self.db.add_items(messages)
            
            processed_conversations.append(conversation)
        
        return processed_conversations

    async def extract_conversations(self, since: Optional[datetime] = None, days: Optional[int] = None) -> List[Conversation]:
        """Extract conversations from Claude and store in the database.
        
        Args:
            since: Only extract conversations since this time.
            days: Only extract conversations from the last N days.
            
        Returns:
            A list of extracted Conversation objects.
        """
        try:
            # Convert days to datetime if provided
            if days is not None and since is None:
                since = datetime.utcnow() - timedelta(days=days)
            
            # Get conversation history
            conversations = await self.get_conversation_history(since)
            
            # Process and store conversations
            processed_conversations = await self.process_conversation_history(conversations)
            
            logger.info(f"Extracted {len(processed_conversations)} conversations from Claude")
            
            return processed_conversations
        except Exception as e:
            logger.error(f"Failed to extract conversations: {e}")
            return []  # Return empty list instead of raising exception for better error handling


async def get_claude_client() -> ClaudeMCPClient:
    """Get a Claude MCP client.
    
    Returns:
        A Claude MCP client.
    """
    db = get_db()
    config = db.get_config()
    
    client = ClaudeMCPClient(
        host=config.mcp_host,
        port=config.mcp_port
    )
    
    return client
