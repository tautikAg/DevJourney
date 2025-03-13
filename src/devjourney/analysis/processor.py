"""
Analysis processor for DevJourney.

This module processes conversations and extracts insights using NLP techniques.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from devjourney.database import get_db
from devjourney.models import (
    Conversation,
    ContentType,
    Insight,
    InsightCategory,
    InsightType,
    Message,
    MessageRole,
    TechnologyTag,
)

logger = logging.getLogger(__name__)


class AnalysisProcessorError(Exception):
    """Exception raised for analysis processor errors."""
    pass


class AnalysisProcessor:
    """Processor for analyzing conversations and extracting insights."""

    def __init__(self, min_confidence_threshold: float = 0.7):
        """Initialize the analysis processor.
        
        Args:
            min_confidence_threshold: The minimum confidence threshold for extracting insights.
        """
        self.db = get_db()
        self.config = self.db.get_config()
        self.min_confidence_threshold = min_confidence_threshold or self.config.min_confidence_threshold

    def _extract_code_blocks(self, message: Message) -> List[Dict[str, Any]]:
        """Extract code blocks from a message.
        
        Args:
            message: The message to extract code blocks from.
            
        Returns:
            A list of code blocks.
        """
        code_blocks = []
        
        for block in message.content_blocks:
            if block.get("type") == ContentType.CODE:
                code_block = {
                    "language": block.get("language", ""),
                    "content": block.get("content", ""),
                }
                code_blocks.append(code_block)
        
        return code_blocks

    def _extract_technologies(self, text: str) -> List[str]:
        """Extract technology mentions from text.
        
        Args:
            text: The text to extract technologies from.
            
        Returns:
            A list of technology names.
        """
        # This is a simple implementation that looks for common technology names
        # In a real implementation, you would use a more sophisticated approach
        common_technologies = [
            "Python", "JavaScript", "TypeScript", "React", "Vue", "Angular",
            "Node.js", "Express", "Django", "Flask", "FastAPI",
            "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis",
            "Docker", "Kubernetes", "AWS", "Azure", "GCP",
            "Git", "GitHub", "GitLab", "Bitbucket",
            "HTML", "CSS", "Sass", "Less", "Tailwind",
            "REST", "GraphQL", "gRPC", "WebSockets",
            "TensorFlow", "PyTorch", "scikit-learn", "Pandas", "NumPy",
            "Java", "C#", "C++", "Go", "Rust", "Swift", "Kotlin",
        ]
        
        found_technologies = set()
        
        for tech in common_technologies:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(tech) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                found_technologies.add(tech)
        
        return list(found_technologies)

    def _determine_category(self, text: str, technologies: List[str]) -> InsightCategory:
        """Determine the category of an insight based on its content.
        
        Args:
            text: The text of the insight.
            technologies: The technologies mentioned in the insight.
            
        Returns:
            The category of the insight.
        """
        # This is a simple implementation that uses keyword matching
        # In a real implementation, you would use a more sophisticated approach
        
        # Check for programming-related keywords
        programming_keywords = [
            "code", "function", "class", "method", "variable", "algorithm",
            "programming", "syntax", "compiler", "interpreter", "runtime",
        ]
        
        # Check for DevOps-related keywords
        devops_keywords = [
            "deploy", "pipeline", "ci/cd", "continuous integration", "continuous deployment",
            "infrastructure", "container", "docker", "kubernetes", "orchestration",
            "monitoring", "logging", "alerting", "scaling", "load balancing",
        ]
        
        # Check for design-related keywords
        design_keywords = [
            "design", "ui", "ux", "user interface", "user experience",
            "wireframe", "mockup", "prototype", "responsive", "accessibility",
            "color", "typography", "layout", "component", "style guide",
        ]
        
        # Check for architecture-related keywords
        architecture_keywords = [
            "architecture", "system design", "microservice", "monolith",
            "scalability", "reliability", "availability", "performance",
            "latency", "throughput", "consistency", "eventual consistency",
            "caching", "sharding", "partitioning", "replication",
        ]
        
        # Check for database-related keywords
        database_keywords = [
            "database", "sql", "nosql", "query", "index", "transaction",
            "acid", "base", "schema", "migration", "orm", "join",
            "primary key", "foreign key", "constraint", "normalization",
        ]
        
        # Check for testing-related keywords
        testing_keywords = [
            "test", "unit test", "integration test", "e2e test", "end-to-end test",
            "mock", "stub", "spy", "assertion", "coverage", "tdd", "bdd",
            "regression", "smoke test", "load test", "stress test",
        ]
        
        # Count the number of matches for each category
        programming_count = sum(1 for kw in programming_keywords if re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE))
        devops_count = sum(1 for kw in devops_keywords if re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE))
        design_count = sum(1 for kw in design_keywords if re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE))
        architecture_count = sum(1 for kw in architecture_keywords if re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE))
        database_count = sum(1 for kw in database_keywords if re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE))
        testing_count = sum(1 for kw in testing_keywords if re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE))
        
        # Also consider the technologies
        for tech in technologies:
            if tech in ["Python", "JavaScript", "TypeScript", "Java", "C#", "C++", "Go", "Rust", "Swift", "Kotlin"]:
                programming_count += 1
            elif tech in ["Docker", "Kubernetes", "AWS", "Azure", "GCP", "Jenkins", "CircleCI", "GitHub Actions"]:
                devops_count += 1
            elif tech in ["HTML", "CSS", "Sass", "Less", "Tailwind", "Bootstrap", "Material-UI"]:
                design_count += 1
            elif tech in ["REST", "GraphQL", "gRPC", "WebSockets", "Kafka", "RabbitMQ"]:
                architecture_count += 1
            elif tech in ["SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch"]:
                database_count += 1
            elif tech in ["Jest", "Mocha", "Chai", "Cypress", "Selenium", "JUnit", "pytest"]:
                testing_count += 1
        
        # Determine the category with the highest count
        counts = {
            InsightCategory.PROGRAMMING: programming_count,
            InsightCategory.DEVOPS: devops_count,
            InsightCategory.DESIGN: design_count,
            InsightCategory.ARCHITECTURE: architecture_count,
            InsightCategory.DATABASE: database_count,
            InsightCategory.TESTING: testing_count,
        }
        
        max_category = max(counts.items(), key=lambda x: x[1])
        
        # If no clear category, use OTHER
        if max_category[1] == 0:
            return InsightCategory.OTHER
        
        return max_category[0]

    def _extract_problem_solution(self, conversation: Conversation) -> List[Insight]:
        """Extract problem-solution pairs from a conversation.
        
        Args:
            conversation: The conversation to extract problem-solution pairs from.
            
        Returns:
            A list of problem-solution insights.
        """
        insights = []
        
        # Group messages by user-assistant pairs
        message_pairs = []
        current_user_message = None
        
        for message in conversation.messages:
            if message.role == MessageRole.USER:
                current_user_message = message
            elif message.role == MessageRole.ASSISTANT and current_user_message:
                message_pairs.append((current_user_message, message))
                current_user_message = None
        
        # Process each message pair
        for user_message, assistant_message in message_pairs:
            # Extract the user's question
            user_text = ""
            for block in user_message.content_blocks:
                if block.get("type") == ContentType.TEXT:
                    user_text += block.get("content", "") + "\n"
            
            # Extract the assistant's answer
            assistant_text = ""
            for block in assistant_message.content_blocks:
                if block.get("type") == ContentType.TEXT:
                    assistant_text += block.get("content", "") + "\n"
            
            # Skip if either message is empty
            if not user_text.strip() or not assistant_text.strip():
                continue
            
            # Check if this looks like a problem-solution pair
            problem_indicators = [
                "how do i", "how to", "what is", "why does", "can you explain",
                "help me", "i'm stuck", "i am stuck", "not working", "error",
                "problem", "issue", "bug", "fix", "solve", "solution",
            ]
            
            is_problem_solution = any(indicator in user_text.lower() for indicator in problem_indicators)
            
            if is_problem_solution:
                # Extract code blocks from the assistant's message
                code_blocks = self._extract_code_blocks(assistant_message)
                
                # Extract technologies
                technologies = self._extract_technologies(user_text + " " + assistant_text)
                
                # Determine the category
                category = self._determine_category(user_text + " " + assistant_text, technologies)
                
                # Create a title from the user's question
                title = user_text.strip().split("\n")[0][:100]
                
                # Combine the user's question and assistant's answer
                content = f"Problem:\n{user_text.strip()}\n\nSolution:\n{assistant_text.strip()}"
                
                # Create the insight
                insight = Insight(
                    conversation_id=conversation.id,
                    type=InsightType.PROBLEM_SOLUTION,
                    category=category,
                    title=title,
                    content=content,
                    code_blocks=code_blocks,
                    confidence_score=0.9 if len(code_blocks) > 0 else 0.7,
                    extracted_at=datetime.utcnow(),
                )
                
                insights.append(insight)
        
        return insights

    def _extract_learnings(self, conversation: Conversation) -> List[Insight]:
        """Extract learnings from a conversation.
        
        Args:
            conversation: The conversation to extract learnings from.
            
        Returns:
            A list of learning insights.
        """
        insights = []
        
        # Look for assistant messages that contain explanations
        for message in conversation.messages:
            if message.role != MessageRole.ASSISTANT:
                continue
            
            # Extract the assistant's text
            assistant_text = ""
            for block in message.content_blocks:
                if block.get("type") == ContentType.TEXT:
                    assistant_text += block.get("content", "") + "\n"
            
            # Skip if the message is empty
            if not assistant_text.strip():
                continue
            
            # Check if this looks like an explanation
            explanation_indicators = [
                "is a", "are a", "refers to", "means", "is defined as",
                "is used for", "are used for", "is responsible for",
                "works by", "functions by", "operates by",
                "in summary", "to summarize", "in conclusion",
                "the key concept", "the main idea", "the important thing",
            ]
            
            paragraphs = assistant_text.split("\n\n")
            
            for paragraph in paragraphs:
                if len(paragraph.strip()) < 100:
                    continue  # Skip short paragraphs
                
                is_explanation = any(indicator in paragraph.lower() for indicator in explanation_indicators)
                
                if is_explanation:
                    # Extract code blocks from the message
                    code_blocks = self._extract_code_blocks(message)
                    
                    # Extract technologies
                    technologies = self._extract_technologies(paragraph)
                    
                    # Determine the category
                    category = self._determine_category(paragraph, technologies)
                    
                    # Create a title from the first sentence
                    first_sentence = paragraph.strip().split(".")[0]
                    title = first_sentence[:100] + ("..." if len(first_sentence) > 100 else "")
                    
                    # Create the insight
                    insight = Insight(
                        conversation_id=conversation.id,
                        type=InsightType.LEARNING,
                        category=category,
                        title=title,
                        content=paragraph.strip(),
                        code_blocks=code_blocks,
                        confidence_score=0.8,
                        extracted_at=datetime.utcnow(),
                    )
                    
                    insights.append(insight)
        
        return insights

    def _extract_code_references(self, conversation: Conversation) -> List[Insight]:
        """Extract code references from a conversation.
        
        Args:
            conversation: The conversation to extract code references from.
            
        Returns:
            A list of code reference insights.
        """
        insights = []
        
        # Look for assistant messages that contain code blocks
        for message in conversation.messages:
            if message.role != MessageRole.ASSISTANT:
                continue
            
            # Extract code blocks from the message
            code_blocks = self._extract_code_blocks(message)
            
            # Skip if there are no code blocks
            if not code_blocks:
                continue
            
            # Extract the assistant's text
            assistant_text = ""
            for block in message.content_blocks:
                if block.get("type") == ContentType.TEXT:
                    assistant_text += block.get("content", "") + "\n"
            
            # Process each code block
            for code_block in code_blocks:
                language = code_block.get("language", "")
                code = code_block.get("content", "")
                
                # Skip if the code block is empty
                if not code.strip():
                    continue
                
                # Extract technologies
                technologies = [language] if language else []
                technologies.extend(self._extract_technologies(assistant_text + " " + code))
                
                # Determine the category
                category = self._determine_category(assistant_text + " " + code, technologies)
                
                # Create a title based on the code
                title = f"Code snippet: {language}" if language else "Code snippet"
                
                # Find the context for this code block
                context = ""
                for block in message.content_blocks:
                    if block.get("type") == ContentType.TEXT:
                        if len(context) < 500:  # Limit context to 500 characters
                            context += block.get("content", "") + "\n"
                
                # Create the insight
                insight = Insight(
                    conversation_id=conversation.id,
                    type=InsightType.CODE_REFERENCE,
                    category=category,
                    title=title,
                    content=context.strip(),
                    code_blocks=[code_block],
                    confidence_score=0.9,
                    extracted_at=datetime.utcnow(),
                )
                
                insights.append(insight)
        
        return insights

    def _extract_project_references(self, conversation: Conversation) -> List[Insight]:
        """Extract project references from a conversation.
        
        Args:
            conversation: The conversation to extract project references from.
            
        Returns:
            A list of project reference insights.
        """
        insights = []
        
        # Look for messages that mention projects
        all_text = ""
        for message in conversation.messages:
            for block in message.content_blocks:
                if block.get("type") == ContentType.TEXT:
                    all_text += block.get("content", "") + "\n"
        
        # Check for project indicators
        project_indicators = [
            "project", "app", "application", "website", "web app",
            "mobile app", "service", "platform", "system", "tool",
        ]
        
        # Extract potential project names using regex
        project_patterns = [
            r'(?:my|our|the)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:project|app|application|website|service|platform|system|tool)',
            r'(?:working on|building|developing|creating)\s+(?:a|an|the)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?:project|app|application|website|service|platform|system|tool)\s+called\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        potential_projects = []
        
        for pattern in project_patterns:
            matches = re.finditer(pattern, all_text, re.IGNORECASE)
            for match in matches:
                project_name = match.group(1)
                if project_name and len(project_name) > 3:  # Avoid very short names
                    potential_projects.append(project_name)
        
        # Process each potential project
        for project_name in set(potential_projects):
            # Extract technologies
            technologies = self._extract_technologies(all_text)
            
            # Determine the category
            category = self._determine_category(all_text, technologies)
            
            # Create the insight
            insight = Insight(
                conversation_id=conversation.id,
                type=InsightType.PROJECT_REFERENCE,
                category=category,
                title=f"Project: {project_name}",
                content=f"Reference to project: {project_name}\n\nContext:\n{all_text[:500]}...",
                code_blocks=[],
                confidence_score=0.7,
                extracted_at=datetime.utcnow(),
            )
            
            insights.append(insight)
        
        return insights

    def process_conversation(self, conversation: Conversation) -> List[Insight]:
        """Process a conversation and extract insights.
        
        Args:
            conversation: The conversation to process.
            
        Returns:
            A list of extracted insights.
        """
        try:
            # Extract different types of insights
            problem_solutions = self._extract_problem_solution(conversation)
            learnings = self._extract_learnings(conversation)
            code_references = self._extract_code_references(conversation)
            project_references = self._extract_project_references(conversation)
            
            # Combine all insights
            all_insights = problem_solutions + learnings + code_references + project_references
            
            # Filter by confidence threshold
            filtered_insights = [
                insight for insight in all_insights
                if insight.confidence_score >= self.min_confidence_threshold
            ]
            
            # Store the insights in the database
            stored_insights = []
            for insight in filtered_insights:
                # Check if a similar insight already exists
                existing_insights = self.db.get_items(
                    Insight,
                    conversation_id=conversation.id,
                    type=insight.type,
                    title=insight.title,
                )
                
                if existing_insights:
                    logger.debug(f"Similar insight already exists: {insight.title}")
                    continue
                
                # Add the insight to the database
                stored_insight = self.db.add_item(insight)
                
                # Process technology tags
                technologies = set()
                for block in insight.content_blocks:
                    if block.get("language"):
                        technologies.add(block.get("language"))
                
                # Extract technologies from the content
                technologies.update(self._extract_technologies(insight.content))
                
                # Add technology tags
                for tech_name in technologies:
                    # Check if the technology tag already exists
                    existing_tags = self.db.get_items(TechnologyTag, name=tech_name)
                    
                    if existing_tags:
                        tag = existing_tags[0]
                    else:
                        # Create a new tag
                        tag = TechnologyTag(name=tech_name)
                        tag = self.db.add_item(tag)
                    
                    # Link the tag to the insight
                    # This would require a custom method to handle the many-to-many relationship
                    # For simplicity, we'll skip this for now
                
                stored_insights.append(stored_insight)
            
            logger.info(f"Extracted {len(stored_insights)} insights from conversation {conversation.id}")
            
            return stored_insights
        except Exception as e:
            logger.error(f"Failed to process conversation {conversation.id}: {e}")
            raise AnalysisProcessorError(f"Failed to process conversation {conversation.id}: {e}")


def get_analysis_processor() -> AnalysisProcessor:
    """Get an analysis processor.
    
    Returns:
        An analysis processor.
    """
    db = get_db()
    config = db.get_config()
    
    processor = AnalysisProcessor(
        min_confidence_threshold=config.min_confidence_threshold
    )
    
    return processor
