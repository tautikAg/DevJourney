"""
Insights module for DevJourney.

This module provides functions for retrieving and querying insights.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

from devjourney.database import get_db
from devjourney.models import Insight, InsightCategory, InsightType

logger = logging.getLogger(__name__)


class InsightsError(Exception):
    """Exception raised for insights errors."""
    pass


def get_insights(
    insight_type: Optional[InsightType] = None,
    category: Optional[InsightCategory] = None,
    conversation_id: Optional[str] = None,
    days: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    search_term: Optional[str] = None,
    min_confidence: float = 0.7,
) -> List[Insight]:
    """Get insights based on various filters.
    
    Args:
        insight_type: Filter by insight type.
        category: Filter by insight category.
        conversation_id: Filter by conversation ID.
        days: Filter by insights extracted in the last N days.
        limit: Maximum number of insights to return.
        offset: Offset for pagination.
        search_term: Search term to filter insights by content.
        min_confidence: Minimum confidence score for insights.
        
    Returns:
        A list of insights.
    """
    try:
        db = get_db()
        
        # Build the filter parameters
        filter_params = {}
        
        if insight_type:
            filter_params["type"] = insight_type
        
        if category:
            filter_params["category"] = category
        
        if conversation_id:
            filter_params["conversation_id"] = conversation_id
        
        if days:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            filter_params["extracted_at_gte"] = cutoff_date
        
        if min_confidence:
            filter_params["confidence_score_gte"] = min_confidence
        
        # Add search term if provided
        if search_term:
            filter_params["content_contains"] = search_term
        
        # Get insights
        insights = db.get_items(
            Insight,
            **filter_params,
            limit=limit,
            offset=offset,
            order_by="extracted_at",
            order_desc=True,
        )
        
        return insights
    except Exception as e:
        logger.error(f"Failed to get insights: {e}")
        raise InsightsError(f"Failed to get insights: {e}")


def get_insight_by_id(insight_id: str) -> Optional[Insight]:
    """Get an insight by ID.
    
    Args:
        insight_id: The ID of the insight to get.
        
    Returns:
        The insight, or None if it doesn't exist.
    """
    try:
        db = get_db()
        
        insights = db.get_items(Insight, id=insight_id)
        
        if not insights:
            return None
        
        return insights[0]
    except Exception as e:
        logger.error(f"Failed to get insight {insight_id}: {e}")
        raise InsightsError(f"Failed to get insight {insight_id}: {e}")


def get_insight_stats(days: Optional[int] = None) -> Dict[str, Union[int, Dict[str, int]]]:
    """Get statistics about insights.
    
    Args:
        days: Filter by insights extracted in the last N days.
        
    Returns:
        A dictionary with insight statistics.
    """
    try:
        db = get_db()
        
        # Build the filter parameters
        filter_params = {}
        
        if days:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            filter_params["extracted_at_gte"] = cutoff_date
        
        # Get all insights
        insights = db.get_items(Insight, **filter_params)
        
        # Calculate statistics
        total_insights = len(insights)
        
        # Count by type
        type_counts = {}
        for insight_type in InsightType:
            type_counts[insight_type.value] = sum(1 for i in insights if i.type == insight_type)
        
        # Count by category
        category_counts = {}
        for category in InsightCategory:
            category_counts[category.value] = sum(1 for i in insights if i.category == category)
        
        # Count by day
        day_counts = {}
        for insight in insights:
            day = insight.extracted_at.date().isoformat()
            day_counts[day] = day_counts.get(day, 0) + 1
        
        # Calculate average confidence score
        avg_confidence = sum(i.confidence_score for i in insights) / total_insights if total_insights > 0 else 0
        
        return {
            "total": total_insights,
            "by_type": type_counts,
            "by_category": category_counts,
            "by_day": day_counts,
            "avg_confidence": avg_confidence,
        }
    except Exception as e:
        logger.error(f"Failed to get insight stats: {e}")
        raise InsightsError(f"Failed to get insight stats: {e}")


def get_daily_summary(date: Optional[datetime] = None) -> Dict[str, Union[str, List[Dict[str, str]]]]:
    """Get a summary of insights for a specific day.
    
    Args:
        date: The date to get the summary for. Defaults to today.
        
    Returns:
        A dictionary with the daily summary.
    """
    try:
        if not date:
            date = datetime.utcnow()
        
        # Get the start and end of the day
        start_of_day = datetime(date.year, date.month, date.day, 0, 0, 0)
        end_of_day = datetime(date.year, date.month, date.day, 23, 59, 59)
        
        db = get_db()
        
        # Get insights for the day
        insights = db.get_items(
            Insight,
            extracted_at_gte=start_of_day,
            extracted_at_lte=end_of_day,
            order_by="confidence_score",
            order_desc=True,
        )
        
        # Group insights by type
        insights_by_type = {}
        for insight in insights:
            if insight.type not in insights_by_type:
                insights_by_type[insight.type] = []
            insights_by_type[insight.type].append(insight)
        
        # Build the summary
        summary = {
            "date": date.date().isoformat(),
            "total_insights": len(insights),
            "problem_solutions": [],
            "learnings": [],
            "code_references": [],
            "project_references": [],
        }
        
        # Add problem solutions
        for insight in insights_by_type.get(InsightType.PROBLEM_SOLUTION, []):
            summary["problem_solutions"].append({
                "id": insight.id,
                "title": insight.title,
                "category": insight.category.value,
                "confidence": insight.confidence_score,
            })
        
        # Add learnings
        for insight in insights_by_type.get(InsightType.LEARNING, []):
            summary["learnings"].append({
                "id": insight.id,
                "title": insight.title,
                "category": insight.category.value,
                "confidence": insight.confidence_score,
            })
        
        # Add code references
        for insight in insights_by_type.get(InsightType.CODE_REFERENCE, []):
            summary["code_references"].append({
                "id": insight.id,
                "title": insight.title,
                "category": insight.category.value,
                "confidence": insight.confidence_score,
            })
        
        # Add project references
        for insight in insights_by_type.get(InsightType.PROJECT_REFERENCE, []):
            summary["project_references"].append({
                "id": insight.id,
                "title": insight.title,
                "category": insight.category.value,
                "confidence": insight.confidence_score,
            })
        
        return summary
    except Exception as e:
        logger.error(f"Failed to get daily summary for {date.date().isoformat()}: {e}")
        raise InsightsError(f"Failed to get daily summary: {e}")


def search_insights(
    query: str,
    insight_type: Optional[InsightType] = None,
    category: Optional[InsightCategory] = None,
    days: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    min_confidence: float = 0.7,
) -> List[Insight]:
    """Search for insights based on a query.
    
    Args:
        query: The search query.
        insight_type: Filter by insight type.
        category: Filter by insight category.
        days: Filter by insights extracted in the last N days.
        limit: Maximum number of insights to return.
        offset: Offset for pagination.
        min_confidence: Minimum confidence score for insights.
        
    Returns:
        A list of insights matching the query.
    """
    return get_insights(
        insight_type=insight_type,
        category=category,
        days=days,
        limit=limit,
        offset=offset,
        search_term=query,
        min_confidence=min_confidence,
    ) 