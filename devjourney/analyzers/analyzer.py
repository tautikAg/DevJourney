"""
Main analyzer for processing conversations and extracting insights.
"""
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path

from devjourney.config.settings import config, CACHE_DIR
from devjourney.models.conversation import Conversation, MessageRole
from devjourney.models.analysis import (
    ContentCategory, ContentItem, ProblemSolution, Learning, 
    CodeReference, MeetingNotes, DailySummary, AnalysisResult
)
from devjourney.analyzers.llm import llm_analyzer
from devjourney.extractors.manager import extractor_manager

logger = logging.getLogger(__name__)

# Cache file for analysis results
ANALYSIS_CACHE_FILE = CACHE_DIR / "analysis_results.json"


class ConversationAnalyzer:
    """Analyzer for extracting insights from conversations."""
    
    def __init__(self):
        """Initialize the conversation analyzer."""
        self.logger = logging.getLogger(__name__)
        self.enabled_categories = set(config.categories.enabled_categories)
        self.custom_categories = set(config.categories.custom_categories)
        self.technology_tags = set(config.categories.technology_tags)
        self.custom_tags = set(config.categories.custom_tags)
        
        self.logger.info(f"Initialized conversation analyzer with {len(self.enabled_categories)} enabled categories")
    
    def analyze_conversations(self, conversations: List[Conversation], 
                             force_refresh: bool = False) -> AnalysisResult:
        """
        Analyze a list of conversations to extract insights.
        
        Args:
            conversations: List of conversations to analyze
            force_refresh: Force refresh analysis instead of using cache
            
        Returns:
            Analysis result containing extracted content items
        """
        if not conversations:
            self.logger.warning("No conversations to analyze")
            return AnalysisResult()
        
        # Check if we can use cached analysis
        if not force_refresh:
            cached_result = self._load_cached_analysis()
            if cached_result:
                # Filter out already analyzed conversations
                analyzed_conv_ids = {item.conversation_id for item in cached_result.content_items}
                new_conversations = [conv for conv in conversations if conv.id not in analyzed_conv_ids]
                
                if not new_conversations:
                    self.logger.info("Using cached analysis results")
                    return cached_result
                
                self.logger.info(
                    f"Found {len(new_conversations)} new conversations to analyze, "
                    f"using {len(cached_result.content_items)} cached items"
                )
                
                # Analyze only new conversations and merge with cached results
                new_result = self._analyze_conversations(new_conversations)
                
                # Merge results
                for item in new_result.content_items:
                    cached_result.add_content_item(item)
                
                # Update daily summaries
                self._update_daily_summaries(cached_result)
                
                # Cache the updated results
                self._cache_analysis(cached_result)
                
                return cached_result
        
        # Analyze all conversations
        result = self._analyze_conversations(conversations)
        
        # Generate daily summaries
        self._update_daily_summaries(result)
        
        # Cache the results
        self._cache_analysis(result)
        
        return result
    
    def _analyze_conversations(self, conversations: List[Conversation]) -> AnalysisResult:
        """
        Analyze conversations to extract insights.
        
        Args:
            conversations: List of conversations to analyze
            
        Returns:
            Analysis result containing extracted content items
        """
        result = AnalysisResult()
        
        for conversation in conversations:
            try:
                # Extract content items from the conversation
                content_items = self._extract_content_items(conversation)
                
                # Add content items to the result
                for item in content_items:
                    result.add_content_item(item)
                
                self.logger.info(
                    f"Extracted {len(content_items)} content items from conversation {conversation.id}"
                )
            except Exception as e:
                self.logger.error(f"Error analyzing conversation {conversation.id}: {str(e)}")
        
        return result
    
    def _extract_content_items(self, conversation: Conversation) -> List[ContentItem]:
        """
        Extract content items from a conversation.
        
        Args:
            conversation: Conversation to analyze
            
        Returns:
            List of extracted content items
        """
        content_items = []
        
        # Skip conversations with too few messages
        if conversation.message_count < 2:
            self.logger.debug(f"Skipping conversation {conversation.id} with only {conversation.message_count} messages")
            return content_items
        
        # Prepare conversation text for analysis
        conversation_text = self._prepare_conversation_text(conversation)
        
        # Analyze the conversation using LLM
        success, analysis_json = self._analyze_with_llm(conversation_text)
        
        if not success:
            self.logger.warning(f"Failed to analyze conversation {conversation.id}")
            return content_items
        
        # Parse the analysis result
        try:
            analysis_data = json.loads(analysis_json)
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in analysis result for conversation {conversation.id}")
            return content_items
        
        # Extract content items from the analysis
        if "problem_solutions" in analysis_data and ContentCategory.PROBLEM_SOLUTION in self.enabled_categories:
            for ps_data in analysis_data.get("problem_solutions", []):
                try:
                    problem_solution = self._create_problem_solution(ps_data, conversation)
                    content_items.append(problem_solution)
                except Exception as e:
                    self.logger.error(f"Error creating problem solution: {str(e)}")
        
        if "learnings" in analysis_data and ContentCategory.LEARNING in self.enabled_categories:
            for learning_data in analysis_data.get("learnings", []):
                try:
                    learning = self._create_learning(learning_data, conversation)
                    content_items.append(learning)
                except Exception as e:
                    self.logger.error(f"Error creating learning: {str(e)}")
        
        if "code_references" in analysis_data and ContentCategory.CODE_REFERENCE in self.enabled_categories:
            for code_data in analysis_data.get("code_references", []):
                try:
                    code_reference = self._create_code_reference(code_data, conversation)
                    content_items.append(code_reference)
                except Exception as e:
                    self.logger.error(f"Error creating code reference: {str(e)}")
        
        if "meeting_notes" in analysis_data and ContentCategory.MEETING_NOTES in self.enabled_categories:
            for meeting_data in analysis_data.get("meeting_notes", []):
                try:
                    meeting_notes = self._create_meeting_notes(meeting_data, conversation)
                    content_items.append(meeting_notes)
                except Exception as e:
                    self.logger.error(f"Error creating meeting notes: {str(e)}")
        
        return content_items
    
    def _prepare_conversation_text(self, conversation: Conversation) -> str:
        """
        Prepare conversation text for analysis.
        
        Args:
            conversation: Conversation to prepare
            
        Returns:
            Formatted conversation text
        """
        lines = [
            f"Conversation Title: {conversation.title}",
            f"Source: {conversation.source.value}",
            f"Date: {conversation.start_time.isoformat()}",
            f"Messages: {conversation.message_count}",
            ""
        ]
        
        for message in conversation.messages:
            role_prefix = "User: " if message.role == MessageRole.USER else "Assistant: "
            
            # Combine all content blocks
            content_text = ""
            for content in message.content:
                if content.is_code:
                    language = f" ({content.language})" if content.language else ""
                    content_text += f"\n```{language}\n{content.text}\n```\n"
                else:
                    content_text += content.text
            
            lines.append(f"{role_prefix}{content_text}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _analyze_with_llm(self, conversation_text: str) -> Tuple[bool, str]:
        """
        Analyze conversation text using LLM.
        
        Args:
            conversation_text: Formatted conversation text
            
        Returns:
            Tuple of (success, analysis_json)
        """
        system_prompt = """
        You are an AI assistant that analyzes conversations between users and AI assistants to extract valuable insights.
        Your task is to identify and extract the following types of content:
        
        1. Problem/Solution pairs: Technical problems and their solutions
        2. Learnings: New concepts or knowledge gained
        3. Code References: Useful code snippets with explanations
        4. Meeting Notes: Action items, decisions, and participants
        
        For each item, extract relevant tags based on technologies mentioned (e.g., JavaScript, Python, AWS, React).
        
        Respond with a JSON object containing arrays for each content type. Include only high-quality, substantive items.
        
        Example response format:
        {
            "problem_solutions": [
                {
                    "title": "Fixing React useEffect dependency array",
                    "problem_statement": "Component re-renders infinitely due to missing dependency",
                    "solution": "Add all dependencies used in the effect to the dependency array",
                    "code_snippets": [{"language": "javascript", "code": "useEffect(() => { ... }, [dependency1, dependency2])"}],
                    "tags": ["React", "JavaScript", "Hooks"]
                }
            ],
            "learnings": [
                {
                    "title": "Understanding Python Decorators",
                    "concept": "Function decorators in Python",
                    "explanation": "Decorators are a way to modify functions using wrapper functions",
                    "examples": ["@classmethod", "@property", "Custom decorators"],
                    "related_concepts": ["Higher-order functions", "Metaprogramming"],
                    "tags": ["Python", "Advanced"]
                }
            ],
            "code_references": [
                {
                    "title": "Efficient string concatenation in Python",
                    "language": "python",
                    "code": "' '.join(['word1', 'word2', 'word3'])",
                    "explanation": "Using join() is more efficient than + operator for multiple strings",
                    "file_path": null,
                    "tags": ["Python", "Performance", "Strings"]
                }
            ],
            "meeting_notes": [
                {
                    "title": "API Design Discussion",
                    "participants": ["User", "Assistant"],
                    "action_items": ["Create OpenAPI spec", "Implement authentication middleware"],
                    "decisions": ["Use REST for public API", "GraphQL for internal services"],
                    "tags": ["API", "Architecture", "Planning"]
                }
            ]
        }
        
        If a category has no relevant items, include an empty array for that category.
        Focus on extracting the most valuable and substantive information.
        """
        
        prompt = f"""
        Please analyze the following conversation and extract valuable insights according to the specified categories.
        
        {conversation_text}
        
        Extract only high-quality, substantive items that would be worth saving for future reference.
        Respond with a JSON object as specified.
        """
        
        return llm_analyzer.analyze(prompt, system_prompt)
    
    def _create_problem_solution(self, data: Dict[str, Any], conversation: Conversation) -> ProblemSolution:
        """
        Create a problem solution from analysis data.
        
        Args:
            data: Problem solution data from analysis
            conversation: Source conversation
            
        Returns:
            ProblemSolution object
        """
        return ProblemSolution(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            category=ContentCategory.PROBLEM_SOLUTION,
            title=data.get("title", "Untitled Problem"),
            content=f"{data.get('problem_statement', '')}\n\n{data.get('solution', '')}",
            timestamp=conversation.end_time or conversation.start_time,
            tags=data.get("tags", []),
            source_message_ids=[msg.id for msg in conversation.messages],
            problem_statement=data.get("problem_statement", ""),
            solution=data.get("solution", ""),
            code_snippets=data.get("code_snippets", []),
            metadata={
                "source": conversation.source.value,
                "conversation_title": conversation.title
            }
        )
    
    def _create_learning(self, data: Dict[str, Any], conversation: Conversation) -> Learning:
        """
        Create a learning from analysis data.
        
        Args:
            data: Learning data from analysis
            conversation: Source conversation
            
        Returns:
            Learning object
        """
        return Learning(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            category=ContentCategory.LEARNING,
            title=data.get("title", "Untitled Learning"),
            content=data.get("explanation", ""),
            timestamp=conversation.end_time or conversation.start_time,
            tags=data.get("tags", []),
            source_message_ids=[msg.id for msg in conversation.messages],
            concept=data.get("concept", ""),
            explanation=data.get("explanation", ""),
            examples=data.get("examples", []),
            related_concepts=data.get("related_concepts", []),
            metadata={
                "source": conversation.source.value,
                "conversation_title": conversation.title
            }
        )
    
    def _create_code_reference(self, data: Dict[str, Any], conversation: Conversation) -> CodeReference:
        """
        Create a code reference from analysis data.
        
        Args:
            data: Code reference data from analysis
            conversation: Source conversation
            
        Returns:
            CodeReference object
        """
        return CodeReference(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            category=ContentCategory.CODE_REFERENCE,
            title=data.get("title", "Untitled Code Reference"),
            content=data.get("code", ""),
            timestamp=conversation.end_time or conversation.start_time,
            tags=data.get("tags", []),
            source_message_ids=[msg.id for msg in conversation.messages],
            language=data.get("language", ""),
            code=data.get("code", ""),
            explanation=data.get("explanation", ""),
            file_path=data.get("file_path"),
            metadata={
                "source": conversation.source.value,
                "conversation_title": conversation.title
            }
        )
    
    def _create_meeting_notes(self, data: Dict[str, Any], conversation: Conversation) -> MeetingNotes:
        """
        Create meeting notes from analysis data.
        
        Args:
            data: Meeting notes data from analysis
            conversation: Source conversation
            
        Returns:
            MeetingNotes object
        """
        return MeetingNotes(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            category=ContentCategory.MEETING_NOTES,
            title=data.get("title", "Untitled Meeting"),
            content="\n".join([
                f"Action Items: {', '.join(data.get('action_items', []))}",
                f"Decisions: {', '.join(data.get('decisions', []))}"
            ]),
            timestamp=conversation.end_time or conversation.start_time,
            tags=data.get("tags", []),
            source_message_ids=[msg.id for msg in conversation.messages],
            participants=data.get("participants", []),
            action_items=data.get("action_items", []),
            decisions=data.get("decisions", []),
            metadata={
                "source": conversation.source.value,
                "conversation_title": conversation.title
            }
        )
    
    def _update_daily_summaries(self, result: AnalysisResult) -> None:
        """
        Update daily summaries in the analysis result.
        
        Args:
            result: Analysis result to update
        """
        # Group content items by date
        items_by_date = {}
        
        for item in result.content_items:
            date_key = item.timestamp.date().isoformat()
            if date_key not in items_by_date:
                items_by_date[date_key] = []
            items_by_date[date_key].append(item)
        
        # Create or update daily summaries
        summaries = []
        
        for date_key, items in items_by_date.items():
            date = datetime.fromisoformat(date_key)
            
            # Count items by category
            problem_count = sum(1 for item in items if item.category == ContentCategory.PROBLEM_SOLUTION)
            learning_count = sum(1 for item in items if item.category == ContentCategory.LEARNING)
            code_count = sum(1 for item in items if item.category == ContentCategory.CODE_REFERENCE)
            meeting_count = sum(1 for item in items if item.category == ContentCategory.MEETING_NOTES)
            
            # Get unique conversation IDs
            conversation_ids = set(item.conversation_id for item in items)
            
            # Generate summary text
            summary_text = (
                f"On {date.strftime('%Y-%m-%d')}, you had {len(conversation_ids)} conversations "
                f"that resulted in {len(items)} insights: {problem_count} problems solved, "
                f"{learning_count} new learnings, {code_count} code references, and "
                f"{meeting_count} meeting notes."
            )
            
            # Generate highlights (top items from each category)
            highlights = []
            
            for category in [ContentCategory.PROBLEM_SOLUTION, ContentCategory.LEARNING, 
                            ContentCategory.CODE_REFERENCE, ContentCategory.MEETING_NOTES]:
                category_items = [item for item in items if item.category == category]
                if category_items:
                    # Sort by complexity (approximated by content length)
                    category_items.sort(key=lambda x: len(x.content), reverse=True)
                    # Take top 2 items
                    for item in category_items[:2]:
                        highlights.append(f"{item.category.value}: {item.title}")
            
            # Create or update summary
            summary = DailySummary(
                id=f"summary_{date_key}",
                date=date,
                conversation_count=len(conversation_ids),
                problem_count=problem_count,
                learning_count=learning_count,
                code_reference_count=code_count,
                meeting_count=meeting_count,
                summary_text=summary_text,
                highlights=highlights,
                content_items=[item.id for item in items]
            )
            
            summaries.append(summary)
        
        # Update the result
        result.daily_summaries = summaries
    
    def _cache_analysis(self, result: AnalysisResult) -> None:
        """
        Cache analysis results to disk.
        
        Args:
            result: Analysis result to cache
        """
        try:
            # Convert to dictionary
            result_dict = result.model_dump()
            
            # Create cache directory if it doesn't exist
            CACHE_DIR.mkdir(exist_ok=True, parents=True)
            
            # Write to cache file
            with open(ANALYSIS_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f)
            
            self.logger.info(
                f"Cached analysis results with {len(result.content_items)} items to {ANALYSIS_CACHE_FILE}"
            )
        except Exception as e:
            self.logger.error(f"Error caching analysis results: {str(e)}")
    
    def _load_cached_analysis(self) -> Optional[AnalysisResult]:
        """
        Load cached analysis results from disk.
        
        Returns:
            Cached analysis results or None if not available
        """
        if not ANALYSIS_CACHE_FILE.exists():
            return None
        
        try:
            # Read from cache file
            with open(ANALYSIS_CACHE_FILE, 'r', encoding='utf-8') as f:
                result_dict = json.load(f)
            
            # Convert to AnalysisResult
            result = AnalysisResult.model_validate(result_dict)
            
            self.logger.info(
                f"Loaded cached analysis results with {len(result.content_items)} items from {ANALYSIS_CACHE_FILE}"
            )
            return result
        except Exception as e:
            self.logger.error(f"Error loading cached analysis results: {str(e)}")
            return None
    
    def clear_cache(self) -> bool:
        """
        Clear the analysis cache.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if ANALYSIS_CACHE_FILE.exists():
                ANALYSIS_CACHE_FILE.unlink()
                self.logger.info(f"Cleared analysis cache at {ANALYSIS_CACHE_FILE}")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing analysis cache: {str(e)}")
            return False
    
    def get_items_by_category(self, result: AnalysisResult, category: ContentCategory) -> List[ContentItem]:
        """
        Get content items by category.
        
        Args:
            result: Analysis result
            category: Category to filter by
            
        Returns:
            List of content items in the specified category
        """
        return result.get_items_by_category(category)


def analyze_recent_conversations(days: int = 7, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Analyze conversations from the last N days.
    
    Args:
        days: Number of days to analyze
        force_refresh: Force refresh from sources instead of using cache
        
    Returns:
        Dictionary with analysis statistics
    """
    logger.info(f"Analyzing conversations from the last {days} days")
    
    # Get the date to extract conversations since
    since = datetime.now() - timedelta(days=days)
    
    # Extract conversations
    conversations = extractor_manager.extract_all(since=since, force_refresh=force_refresh)
    logger.info(f"Extracted {len(conversations)} conversations")
    
    if not conversations:
        return {
            "conversations_analyzed": 0,
            "problems_identified": 0,
            "learnings_extracted": 0,
            "code_references": 0,
            "meeting_notes": 0
        }
    
    # Analyze conversations
    analyzer = ConversationAnalyzer()
    result = analyzer.analyze_conversations(conversations, force_refresh=force_refresh)
    
    # Count items by category
    problem_count = len(result.get_items_by_category(ContentCategory.PROBLEM_SOLUTION))
    learning_count = len(result.get_items_by_category(ContentCategory.LEARNING))
    code_count = len(result.get_items_by_category(ContentCategory.CODE_REFERENCE))
    meeting_count = len(result.get_items_by_category(ContentCategory.MEETING_NOTES))
    
    return {
        "conversations_analyzed": len(conversations),
        "problems_identified": problem_count,
        "learnings_extracted": learning_count,
        "code_references": code_count,
        "meeting_notes": meeting_count
    }


# Singleton instance
conversation_analyzer = ConversationAnalyzer() 