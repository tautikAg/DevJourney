"""
Formatter for converting data models to Notion format.
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple

from devjourney.models.analysis import (
    ContentCategory, ContentItem, ProblemSolution, Learning, 
    CodeReference, MeetingNotes, DailySummary
)

logger = logging.getLogger(__name__)


class NotionFormatter:
    """Formatter for converting data models to Notion format."""
    
    @staticmethod
    def format_title(text: str) -> Dict[str, Any]:
        """
        Format text as a Notion title property.
        
        Args:
            text: Text to format
            
        Returns:
            Formatted title property
        """
        return {
            "title": [
                {
                    "text": {
                        "content": text
                    }
                }
            ]
        }
    
    @staticmethod
    def format_rich_text(text: str) -> Dict[str, Any]:
        """
        Format text as a Notion rich text property.
        
        Args:
            text: Text to format
            
        Returns:
            Formatted rich text property
        """
        # Split text into chunks to avoid Notion's 2000 character limit
        chunks = []
        max_chunk_size = 1900  # Leave some room for overhead
        
        for i in range(0, len(text), max_chunk_size):
            chunk = text[i:i + max_chunk_size]
            chunks.append({"text": {"content": chunk}})
        
        return {
            "rich_text": chunks
        }
    
    @staticmethod
    def format_date(date: datetime) -> Dict[str, Any]:
        """
        Format date as a Notion date property.
        
        Args:
            date: Date to format
            
        Returns:
            Formatted date property
        """
        return {
            "date": {
                "start": date.isoformat()
            }
        }
    
    @staticmethod
    def format_number(number: int) -> Dict[str, Any]:
        """
        Format number as a Notion number property.
        
        Args:
            number: Number to format
            
        Returns:
            Formatted number property
        """
        return {
            "number": number
        }
    
    @staticmethod
    def format_select(option: str) -> Dict[str, Any]:
        """
        Format option as a Notion select property.
        
        Args:
            option: Option to format
            
        Returns:
            Formatted select property
        """
        return {
            "select": {
                "name": option
            }
        }
    
    @staticmethod
    def format_multi_select(options: List[str]) -> Dict[str, Any]:
        """
        Format options as a Notion multi-select property.
        
        Args:
            options: Options to format
            
        Returns:
            Formatted multi-select property
        """
        return {
            "multi_select": [
                {"name": option} for option in options
            ]
        }
    
    @staticmethod
    def format_url(url: str) -> Dict[str, Any]:
        """
        Format URL as a Notion URL property.
        
        Args:
            url: URL to format
            
        Returns:
            Formatted URL property
        """
        return {
            "url": url
        }
    
    @staticmethod
    def format_checkbox(checked: bool) -> Dict[str, Any]:
        """
        Format boolean as a Notion checkbox property.
        
        Args:
            checked: Boolean value
            
        Returns:
            Formatted checkbox property
        """
        return {
            "checkbox": checked
        }
    
    @staticmethod
    def format_code_block(code: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Format code as a Notion code block.
        
        Args:
            code: Code to format
            language: Programming language
            
        Returns:
            Formatted code block
        """
        return {
            "type": "code",
            "code": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": code
                        }
                    }
                ],
                "language": language or "plain text"
            }
        }
    
    @staticmethod
    def format_paragraph(text: str) -> Dict[str, Any]:
        """
        Format text as a Notion paragraph block.
        
        Args:
            text: Text to format
            
        Returns:
            Formatted paragraph block
        """
        return {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": text
                        }
                    }
                ]
            }
        }
    
    @staticmethod
    def format_heading(text: str, level: int = 2) -> Dict[str, Any]:
        """
        Format text as a Notion heading block.
        
        Args:
            text: Text to format
            level: Heading level (1, 2, or 3)
            
        Returns:
            Formatted heading block
        """
        heading_type = f"heading_{level}"
        return {
            "type": heading_type,
            heading_type: {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": text
                        }
                    }
                ]
            }
        }
    
    @staticmethod
    def format_bulleted_list(items: List[str]) -> List[Dict[str, Any]]:
        """
        Format items as Notion bulleted list blocks.
        
        Args:
            items: Items to format
            
        Returns:
            List of formatted bulleted list blocks
        """
        return [
            {
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": item
                            }
                        }
                    ]
                }
            }
            for item in items
        ]
    
    @staticmethod
    def format_numbered_list(items: List[str]) -> List[Dict[str, Any]]:
        """
        Format items as Notion numbered list blocks.
        
        Args:
            items: Items to format
            
        Returns:
            List of formatted numbered list blocks
        """
        return [
            {
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": item
                            }
                        }
                    ]
                }
            }
            for item in items
        ]
    
    @staticmethod
    def format_toggle(summary: str, content: str) -> Dict[str, Any]:
        """
        Format text as a Notion toggle block.
        
        Args:
            summary: Toggle summary
            content: Toggle content
            
        Returns:
            Formatted toggle block
        """
        return {
            "type": "toggle",
            "toggle": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": summary
                        }
                    }
                ],
                "children": [
                    {
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": content
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
    
    @staticmethod
    def format_divider() -> Dict[str, Any]:
        """
        Format a Notion divider block.
        
        Returns:
            Formatted divider block
        """
        return {
            "type": "divider",
            "divider": {}
        }
    
    @staticmethod
    def format_daily_summary(summary: DailySummary) -> Dict[str, Dict[str, Any]]:
        """
        Format a daily summary as Notion page properties.
        
        Args:
            summary: Daily summary to format
            
        Returns:
            Formatted page properties
        """
        properties = {
            "Name": NotionFormatter.format_title(f"Daily Summary: {summary.date.strftime('%Y-%m-%d')}"),
            "Date": NotionFormatter.format_date(summary.date),
            "Conversations": NotionFormatter.format_number(summary.conversation_count),
            "Problems Solved": NotionFormatter.format_number(summary.problem_count),
            "Learnings": NotionFormatter.format_number(summary.learning_count),
            "Code References": NotionFormatter.format_number(summary.code_reference_count),
            "Meetings": NotionFormatter.format_number(summary.meeting_count),
            "Summary": NotionFormatter.format_rich_text(summary.summary_text)
        }
        
        if summary.highlights:
            properties["Highlights"] = NotionFormatter.format_rich_text("\n".join(summary.highlights))
        
        return properties
    
    @staticmethod
    def format_daily_summary_content(summary: DailySummary) -> List[Dict[str, Any]]:
        """
        Format a daily summary as Notion page content.
        
        Args:
            summary: Daily summary to format
            
        Returns:
            Formatted page content
        """
        content = [
            NotionFormatter.format_heading(f"Daily Summary: {summary.date.strftime('%Y-%m-%d')}", 1),
            NotionFormatter.format_paragraph(summary.summary_text),
            NotionFormatter.format_divider()
        ]
        
        if summary.highlights:
            content.append(NotionFormatter.format_heading("Highlights", 2))
            content.extend(NotionFormatter.format_bulleted_list(summary.highlights))
            content.append(NotionFormatter.format_divider())
        
        return content
    
    @staticmethod
    def format_problem_solution(problem: ProblemSolution) -> Dict[str, Dict[str, Any]]:
        """
        Format a problem solution as Notion page properties.
        
        Args:
            problem: Problem solution to format
            
        Returns:
            Formatted page properties
        """
        properties = {
            "Name": NotionFormatter.format_title(problem.title),
            "Date": NotionFormatter.format_date(problem.timestamp),
            "Problem": NotionFormatter.format_rich_text(problem.problem_statement),
            "Solution": NotionFormatter.format_rich_text(problem.solution)
        }
        
        if problem.tags:
            properties["Tags"] = NotionFormatter.format_multi_select(problem.tags)
        
        if problem.metadata and "source" in problem.metadata:
            properties["Source"] = NotionFormatter.format_select(problem.metadata["source"])
        
        return properties
    
    @staticmethod
    def format_problem_solution_content(problem: ProblemSolution) -> List[Dict[str, Any]]:
        """
        Format a problem solution as Notion page content.
        
        Args:
            problem: Problem solution to format
            
        Returns:
            Formatted page content
        """
        content = [
            NotionFormatter.format_heading(problem.title, 1),
            NotionFormatter.format_heading("Problem", 2),
            NotionFormatter.format_paragraph(problem.problem_statement),
            NotionFormatter.format_heading("Solution", 2),
            NotionFormatter.format_paragraph(problem.solution)
        ]
        
        if problem.code_snippets:
            content.append(NotionFormatter.format_heading("Code Snippets", 2))
            
            for snippet in problem.code_snippets:
                if isinstance(snippet, dict):
                    language = snippet.get("language", "plain text")
                    code = snippet.get("code", "")
                    content.append(NotionFormatter.format_code_block(code, language))
        
        if problem.metadata and "conversation_title" in problem.metadata:
            content.append(NotionFormatter.format_divider())
            content.append(
                NotionFormatter.format_paragraph(
                    f"Source: {problem.metadata.get('source', 'Unknown')} - "
                    f"{problem.metadata.get('conversation_title', 'Untitled Conversation')}"
                )
            )
        
        return content
    
    @staticmethod
    def format_learning(learning: Learning) -> Dict[str, Dict[str, Any]]:
        """
        Format a learning as Notion page properties.
        
        Args:
            learning: Learning to format
            
        Returns:
            Formatted page properties
        """
        properties = {
            "Name": NotionFormatter.format_title(learning.title),
            "Date": NotionFormatter.format_date(learning.timestamp),
            "Concept": NotionFormatter.format_rich_text(learning.concept),
            "Explanation": NotionFormatter.format_rich_text(learning.explanation)
        }
        
        if learning.examples:
            properties["Examples"] = NotionFormatter.format_rich_text("\n".join(learning.examples))
        
        if learning.tags:
            properties["Tags"] = NotionFormatter.format_multi_select(learning.tags)
        
        if learning.metadata and "source" in learning.metadata:
            properties["Source"] = NotionFormatter.format_select(learning.metadata["source"])
        
        return properties
    
    @staticmethod
    def format_learning_content(learning: Learning) -> List[Dict[str, Any]]:
        """
        Format a learning as Notion page content.
        
        Args:
            learning: Learning to format
            
        Returns:
            Formatted page content
        """
        content = [
            NotionFormatter.format_heading(learning.title, 1),
            NotionFormatter.format_heading("Concept", 2),
            NotionFormatter.format_paragraph(learning.concept),
            NotionFormatter.format_heading("Explanation", 2),
            NotionFormatter.format_paragraph(learning.explanation)
        ]
        
        if learning.examples:
            content.append(NotionFormatter.format_heading("Examples", 2))
            content.extend(NotionFormatter.format_bulleted_list(learning.examples))
        
        if learning.related_concepts:
            content.append(NotionFormatter.format_heading("Related Concepts", 2))
            content.extend(NotionFormatter.format_bulleted_list(learning.related_concepts))
        
        if learning.metadata and "conversation_title" in learning.metadata:
            content.append(NotionFormatter.format_divider())
            content.append(
                NotionFormatter.format_paragraph(
                    f"Source: {learning.metadata.get('source', 'Unknown')} - "
                    f"{learning.metadata.get('conversation_title', 'Untitled Conversation')}"
                )
            )
        
        return content
    
    @staticmethod
    def format_code_reference(code_ref: CodeReference) -> Dict[str, Dict[str, Any]]:
        """
        Format a code reference as Notion page properties.
        
        Args:
            code_ref: Code reference to format
            
        Returns:
            Formatted page properties
        """
        properties = {
            "Name": NotionFormatter.format_title(code_ref.title),
            "Date": NotionFormatter.format_date(code_ref.timestamp),
            "Language": NotionFormatter.format_select(code_ref.language or "Other"),
            "Code": NotionFormatter.format_rich_text(code_ref.code),
            "Explanation": NotionFormatter.format_rich_text(code_ref.explanation)
        }
        
        if code_ref.file_path:
            properties["File Path"] = NotionFormatter.format_rich_text(code_ref.file_path)
        
        if code_ref.tags:
            properties["Tags"] = NotionFormatter.format_multi_select(code_ref.tags)
        
        if code_ref.metadata and "source" in code_ref.metadata:
            properties["Source"] = NotionFormatter.format_select(code_ref.metadata["source"])
        
        return properties
    
    @staticmethod
    def format_code_reference_content(code_ref: CodeReference) -> List[Dict[str, Any]]:
        """
        Format a code reference as Notion page content.
        
        Args:
            code_ref: Code reference to format
            
        Returns:
            Formatted page content
        """
        content = [
            NotionFormatter.format_heading(code_ref.title, 1)
        ]
        
        if code_ref.file_path:
            content.append(NotionFormatter.format_paragraph(f"File: {code_ref.file_path}"))
        
        content.append(NotionFormatter.format_heading("Code", 2))
        content.append(NotionFormatter.format_code_block(code_ref.code, code_ref.language))
        
        content.append(NotionFormatter.format_heading("Explanation", 2))
        content.append(NotionFormatter.format_paragraph(code_ref.explanation))
        
        if code_ref.metadata and "conversation_title" in code_ref.metadata:
            content.append(NotionFormatter.format_divider())
            content.append(
                NotionFormatter.format_paragraph(
                    f"Source: {code_ref.metadata.get('source', 'Unknown')} - "
                    f"{code_ref.metadata.get('conversation_title', 'Untitled Conversation')}"
                )
            )
        
        return content
    
    @staticmethod
    def format_meeting_notes(meeting: MeetingNotes) -> Dict[str, Dict[str, Any]]:
        """
        Format meeting notes as Notion page properties.
        
        Args:
            meeting: Meeting notes to format
            
        Returns:
            Formatted page properties
        """
        properties = {
            "Name": NotionFormatter.format_title(meeting.title),
            "Date": NotionFormatter.format_date(meeting.timestamp)
        }
        
        if meeting.participants:
            properties["Participants"] = NotionFormatter.format_rich_text(", ".join(meeting.participants))
        
        if meeting.action_items:
            properties["Action Items"] = NotionFormatter.format_rich_text("\n".join(meeting.action_items))
        
        if meeting.decisions:
            properties["Decisions"] = NotionFormatter.format_rich_text("\n".join(meeting.decisions))
        
        if meeting.tags:
            properties["Tags"] = NotionFormatter.format_multi_select(meeting.tags)
        
        if meeting.metadata and "source" in meeting.metadata:
            properties["Source"] = NotionFormatter.format_select(meeting.metadata["source"])
        
        return properties
    
    @staticmethod
    def format_meeting_notes_content(meeting: MeetingNotes) -> List[Dict[str, Any]]:
        """
        Format meeting notes as Notion page content.
        
        Args:
            meeting: Meeting notes to format
            
        Returns:
            Formatted page content
        """
        content = [
            NotionFormatter.format_heading(meeting.title, 1)
        ]
        
        if meeting.participants:
            content.append(NotionFormatter.format_heading("Participants", 2))
            content.extend(NotionFormatter.format_bulleted_list(meeting.participants))
        
        if meeting.action_items:
            content.append(NotionFormatter.format_heading("Action Items", 2))
            content.extend(NotionFormatter.format_bulleted_list(meeting.action_items))
        
        if meeting.decisions:
            content.append(NotionFormatter.format_heading("Decisions", 2))
            content.extend(NotionFormatter.format_bulleted_list(meeting.decisions))
        
        if meeting.metadata and "conversation_title" in meeting.metadata:
            content.append(NotionFormatter.format_divider())
            content.append(
                NotionFormatter.format_paragraph(
                    f"Source: {meeting.metadata.get('source', 'Unknown')} - "
                    f"{meeting.metadata.get('conversation_title', 'Untitled Conversation')}"
                )
            )
        
        return content
    
    @staticmethod
    def format_content_item(item: ContentItem) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Format a content item as Notion page properties and content.
        
        Args:
            item: Content item to format
            
        Returns:
            Tuple of (properties, content)
        """
        if isinstance(item, ProblemSolution):
            return (
                NotionFormatter.format_problem_solution(item),
                NotionFormatter.format_problem_solution_content(item)
            )
        elif isinstance(item, Learning):
            return (
                NotionFormatter.format_learning(item),
                NotionFormatter.format_learning_content(item)
            )
        elif isinstance(item, CodeReference):
            return (
                NotionFormatter.format_code_reference(item),
                NotionFormatter.format_code_reference_content(item)
            )
        elif isinstance(item, MeetingNotes):
            return (
                NotionFormatter.format_meeting_notes(item),
                NotionFormatter.format_meeting_notes_content(item)
            )
        else:
            # Generic content item
            properties = {
                "Name": NotionFormatter.format_title(item.title),
                "Date": NotionFormatter.format_date(item.timestamp),
                "Content": NotionFormatter.format_rich_text(item.content)
            }
            
            if item.tags:
                properties["Tags"] = NotionFormatter.format_multi_select(item.tags)
            
            content = [
                NotionFormatter.format_heading(item.title, 1),
                NotionFormatter.format_paragraph(item.content)
            ]
            
            return properties, content 