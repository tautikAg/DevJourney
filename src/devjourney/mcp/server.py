"""
MCP server implementation for DevJourney.

This module implements a server for the Model Context Protocol (MCP)
to provide tools for interacting with the DevJourney application.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from mcp.server import Server
from mcp.types import EmbeddedResource, Resource, TextContent, Tool

from devjourney.database import get_db
from devjourney.models import Conversation, ConversationSource, DailyLog, Insight, InsightType

logger = logging.getLogger(__name__)


class DevJourneyMCPServer:
    """MCP server for DevJourney application."""

    def __init__(self):
        """Initialize the DevJourney MCP server."""
        self.server = Server("devjourney")
        self.db = get_db()
        self.config = self.db.get_config()
        
        # Register handlers
        self.server.list_tools(self.list_tools)
        self.server.call_tool(self.call_tool)

    async def list_tools(self) -> List[Tool]:
        """List available tools.
        
        Returns:
            A list of available tools.
        """
        return [
            Tool(
                name="get_daily_summary",
                description="Get a summary of your progress for a specific day",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "The date to get the summary for (YYYY-MM-DD format). Defaults to today."
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="get_insights",
                description="Get insights extracted from your conversations",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "The type of insights to get (problem_solution, learning, code_reference, project_reference). If not specified, returns all types."
                        },
                        "limit": {
                            "type": "integer",
                            "description": "The maximum number of insights to return. Defaults to 10."
                        },
                        "offset": {
                            "type": "integer",
                            "description": "The number of insights to skip. Defaults to 0."
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="get_conversations",
                description="Get your conversation history",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "The source of the conversations (claude, cursor). If not specified, returns all sources."
                        },
                        "since": {
                            "type": "string",
                            "description": "Only get conversations since this time (ISO format)."
                        },
                        "limit": {
                            "type": "integer",
                            "description": "The maximum number of conversations to return. Defaults to 10."
                        },
                        "offset": {
                            "type": "integer",
                            "description": "The number of conversations to skip. Defaults to 0."
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="sync_now",
                description="Trigger a manual sync with Notion",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="get_sync_status",
                description="Get the current sync status",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        ]

    async def call_tool(self, name: str, arguments: Any) -> Sequence[TextContent | EmbeddedResource]:
        """Call a tool.
        
        Args:
            name: The name of the tool to call.
            arguments: The arguments to pass to the tool.
            
        Returns:
            The tool call result.
        """
        try:
            if name == "get_daily_summary":
                return await self._get_daily_summary(arguments)
            elif name == "get_insights":
                return await self._get_insights(arguments)
            elif name == "get_conversations":
                return await self._get_conversations(arguments)
            elif name == "sync_now":
                return await self._sync_now(arguments)
            elif name == "get_sync_status":
                return await self._get_sync_status(arguments)
            else:
                return [
                    TextContent(
                        type="text",
                        text=f"Unknown tool: {name}"
                    )
                ]
        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"Error calling tool {name}: {e}"
                )
            ]

    async def _get_daily_summary(self, arguments: Dict[str, Any]) -> Sequence[TextContent | EmbeddedResource]:
        """Get a daily summary.
        
        Args:
            arguments: The arguments for the tool call.
            
        Returns:
            The daily summary.
        """
        date_str = arguments.get("date")
        
        if date_str:
            try:
                date = datetime.fromisoformat(date_str)
            except ValueError:
                return [
                    TextContent(
                        type="text",
                        text=f"Invalid date format: {date_str}. Please use YYYY-MM-DD format."
                    )
                ]
        else:
            date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get the daily log from the database
        daily_logs = self.db.get_items(DailyLog, date=date)
        
        if not daily_logs:
            return [
                TextContent(
                    type="text",
                    text=f"No daily log found for {date.date()}."
                )
            ]
        
        daily_log = daily_logs[0]
        
        # Format the daily summary
        summary = {
            "date": daily_log.date.isoformat(),
            "summary": daily_log.summary,
            "stats": {
                "conversations": daily_log.conversation_count,
                "insights": daily_log.insight_count,
                "problem_solutions": daily_log.problem_solution_count,
                "learnings": daily_log.learning_count,
                "code_references": daily_log.code_reference_count,
                "project_references": daily_log.project_reference_count
            },
            "notion_page_id": daily_log.notion_page_id,
            "last_synced": daily_log.last_synced.isoformat() if daily_log.last_synced else None
        }
        
        return [
            TextContent(
                type="text",
                text=json.dumps(summary, indent=2)
            )
        ]

    async def _get_insights(self, arguments: Dict[str, Any]) -> Sequence[TextContent | EmbeddedResource]:
        """Get insights.
        
        Args:
            arguments: The arguments for the tool call.
            
        Returns:
            The insights.
        """
        insight_type_str = arguments.get("type")
        limit = int(arguments.get("limit", 10))
        offset = int(arguments.get("offset", 0))
        
        # Get insights from the database
        if insight_type_str:
            try:
                insight_type = InsightType(insight_type_str)
                insights = self.db.get_items(Insight, type=insight_type)
            except ValueError:
                return [
                    TextContent(
                        type="text",
                        text=f"Invalid insight type: {insight_type_str}. Valid types are: {', '.join([t.value for t in InsightType])}"
                    )
                ]
        else:
            insights = self.db.get_items(Insight)
        
        # Apply limit and offset
        insights = insights[offset:offset + limit]
        
        # Format the insights
        formatted_insights = []
        for insight in insights:
            formatted_insight = {
                "id": insight.id,
                "type": insight.type.value,
                "category": insight.category.value,
                "title": insight.title,
                "content": insight.content,
                "code_blocks": insight.code_blocks,
                "confidence_score": insight.confidence_score,
                "extracted_at": insight.extracted_at.isoformat(),
                "notion_page_id": insight.notion_page_id,
                "last_synced": insight.last_synced.isoformat() if insight.last_synced else None
            }
            
            formatted_insights.append(formatted_insight)
        
        return [
            TextContent(
                type="text",
                text=json.dumps(formatted_insights, indent=2)
            )
        ]

    async def _get_conversations(self, arguments: Dict[str, Any]) -> Sequence[TextContent | EmbeddedResource]:
        """Get conversations.
        
        Args:
            arguments: The arguments for the tool call.
            
        Returns:
            The conversations.
        """
        source_str = arguments.get("source")
        since_str = arguments.get("since")
        limit = int(arguments.get("limit", 10))
        offset = int(arguments.get("offset", 0))
        
        # Parse source
        if source_str:
            try:
                source = ConversationSource(source_str)
                conversations = self.db.get_items(Conversation, source=source)
            except ValueError:
                return [
                    TextContent(
                        type="text",
                        text=f"Invalid source: {source_str}. Valid sources are: {', '.join([s.value for s in ConversationSource])}"
                    )
                ]
        else:
            conversations = self.db.get_items(Conversation)
        
        # Filter by time if needed
        if since_str:
            try:
                since = datetime.fromisoformat(since_str)
                conversations = [conv for conv in conversations if conv.start_time >= since]
            except ValueError:
                return [
                    TextContent(
                        type="text",
                        text=f"Invalid date format for 'since': {since_str}. Please use ISO format."
                    )
                ]
        
        # Apply limit and offset
        conversations = conversations[offset:offset + limit]
        
        # Format the conversations
        formatted_conversations = []
        for conversation in conversations:
            formatted_conversation = {
                "id": conversation.id,
                "source": conversation.source.value,
                "source_id": conversation.source_id,
                "title": conversation.title,
                "start_time": conversation.start_time.isoformat(),
                "end_time": conversation.end_time.isoformat() if conversation.end_time else None,
                "message_count": len(conversation.messages)
            }
            
            formatted_conversations.append(formatted_conversation)
        
        return [
            TextContent(
                type="text",
                text=json.dumps(formatted_conversations, indent=2)
            )
        ]

    async def _sync_now(self, arguments: Dict[str, Any]) -> Sequence[TextContent | EmbeddedResource]:
        """Trigger a manual sync.
        
        Args:
            arguments: The arguments for the tool call.
            
        Returns:
            The sync result.
        """
        # In a real implementation, this would trigger the sync process
        # For now, we'll just return a message
        return [
            TextContent(
                type="text",
                text="Sync triggered. This is a placeholder for the actual sync process."
            )
        ]

    async def _get_sync_status(self, arguments: Dict[str, Any]) -> Sequence[TextContent | EmbeddedResource]:
        """Get the sync status.
        
        Args:
            arguments: The arguments for the tool call.
            
        Returns:
            The sync status.
        """
        sync_status = self.db.get_sync_status()
        
        status = {
            "last_sync_time": sync_status.last_sync_time.isoformat() if sync_status.last_sync_time else None,
            "last_sync_status": sync_status.last_sync_status,
            "last_error": sync_status.last_error,
            "conversations_processed": sync_status.conversations_processed,
            "insights_extracted": sync_status.insights_extracted,
            "notion_pages_created": sync_status.notion_pages_created,
            "notion_pages_updated": sync_status.notion_pages_updated
        }
        
        return [
            TextContent(
                type="text",
                text=json.dumps(status, indent=2)
            )
        ]

    async def run(self, read_stream: asyncio.StreamReader, write_stream: asyncio.StreamWriter) -> None:
        """Run the MCP server.
        
        Args:
            read_stream: The input stream.
            write_stream: The output stream.
        """
        await self.server.run(
            read_stream,
            write_stream,
            self.server.create_initialization_options()
        )


async def run_mcp_server() -> None:
    """Run the MCP server using stdio."""
    from mcp.server.stdio import stdio_server
    
    server = DevJourneyMCPServer()
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)
