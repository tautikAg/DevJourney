"""
Main analysis module for DevJourney.

This module coordinates the processing of conversations and extraction of insights.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional

from devjourney.database import get_db
from devjourney.models import Conversation, Insight, SyncStatus
from devjourney.analysis.processor import get_analysis_processor

logger = logging.getLogger(__name__)


class AnalysisError(Exception):
    """Exception raised for analysis errors."""
    pass


def process_new_conversations(limit: int = 100) -> List[Conversation]:
    """Process new conversations that haven't been analyzed yet.
    
    Args:
        limit: The maximum number of conversations to process.
        
    Returns:
        A list of processed conversations.
    """
    try:
        db = get_db()
        processor = get_analysis_processor()
        
        # Get conversations that haven't been processed
        unprocessed_conversations = db.get_items(
            Conversation,
            processed=False,
            limit=limit,
            order_by="timestamp",
            order_desc=False,
        )
        
        if not unprocessed_conversations:
            logger.info("No new conversations to process")
            return []
        
        logger.info(f"Processing {len(unprocessed_conversations)} new conversations")
        
        processed_conversations = []
        for conversation in unprocessed_conversations:
            # Process the conversation
            insights = processor.process_conversation(conversation)
            
            # Mark the conversation as processed
            conversation.processed = True
            conversation.processed_at = datetime.utcnow()
            db.update_item(conversation)
            
            processed_conversations.append(conversation)
            
            logger.info(f"Processed conversation {conversation.id} with {len(insights)} insights")
        
        return processed_conversations
    except Exception as e:
        logger.error(f"Failed to process new conversations: {e}")
        raise AnalysisError(f"Failed to process new conversations: {e}")


def reprocess_conversations(days: int = 7, limit: int = 50) -> List[Conversation]:
    """Reprocess conversations that were processed more than the specified number of days ago.
    
    Args:
        days: The number of days to look back.
        limit: The maximum number of conversations to reprocess.
        
    Returns:
        A list of reprocessed conversations.
    """
    try:
        db = get_db()
        processor = get_analysis_processor()
        
        # Calculate the cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get conversations that were processed before the cutoff date
        old_conversations = db.get_items(
            Conversation,
            processed=True,
            processed_at_lt=cutoff_date,
            limit=limit,
            order_by="processed_at",
            order_desc=False,
        )
        
        if not old_conversations:
            logger.info(f"No conversations to reprocess from the last {days} days")
            return []
        
        logger.info(f"Reprocessing {len(old_conversations)} conversations from the last {days} days")
        
        reprocessed_conversations = []
        for conversation in old_conversations:
            # Delete existing insights for this conversation
            db.delete_items(Insight, conversation_id=conversation.id)
            
            # Process the conversation again
            insights = processor.process_conversation(conversation)
            
            # Update the processed timestamp
            conversation.processed_at = datetime.utcnow()
            db.update_item(conversation)
            
            reprocessed_conversations.append(conversation)
            
            logger.info(f"Reprocessed conversation {conversation.id} with {len(insights)} insights")
        
        return reprocessed_conversations
    except Exception as e:
        logger.error(f"Failed to reprocess conversations: {e}")
        raise AnalysisError(f"Failed to reprocess conversations: {e}")


def process_specific_conversation(conversation_id: str) -> Optional[Conversation]:
    """Process a specific conversation.
    
    Args:
        conversation_id: The ID of the conversation to process.
        
    Returns:
        The processed conversation, or None if the conversation doesn't exist.
    """
    try:
        db = get_db()
        processor = get_analysis_processor()
        
        # Get the conversation
        conversations = db.get_items(Conversation, id=conversation_id)
        
        if not conversations:
            logger.warning(f"Conversation {conversation_id} not found")
            return None
        
        conversation = conversations[0]
        
        # Delete existing insights for this conversation
        db.delete_items(Insight, conversation_id=conversation.id)
        
        # Process the conversation
        insights = processor.process_conversation(conversation)
        
        # Mark the conversation as processed
        conversation.processed = True
        conversation.processed_at = datetime.utcnow()
        db.update_item(conversation)
        
        logger.info(f"Processed conversation {conversation.id} with {len(insights)} insights")
        
        return conversation
    except Exception as e:
        logger.error(f"Failed to process conversation {conversation_id}: {e}")
        raise AnalysisError(f"Failed to process conversation {conversation_id}: {e}")


def run_analysis_job():
    """Run the analysis job to process conversations and extract insights."""
    try:
        db = get_db()
        config = db.get_config()
        
        # Update sync status
        sync_status = SyncStatus(
            component="analysis",
            status="running",
            last_run=datetime.utcnow(),
            details="Starting analysis job",
        )
        db.update_or_create_item(sync_status, component="analysis")
        
        start_time = time.time()
        
        # Process new conversations
        new_conversations = process_new_conversations(limit=config.analysis_batch_size)
        
        # Reprocess old conversations if enabled
        reprocessed_conversations = []
        if config.enable_reprocessing:
            reprocessed_conversations = reprocess_conversations(
                days=config.reprocessing_days,
                limit=config.reprocessing_batch_size,
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Update sync status
        sync_status = SyncStatus(
            component="analysis",
            status="completed",
            last_run=datetime.utcnow(),
            details=(
                f"Processed {len(new_conversations)} new conversations and "
                f"reprocessed {len(reprocessed_conversations)} conversations "
                f"in {duration:.2f} seconds"
            ),
        )
        db.update_or_create_item(sync_status, component="analysis")
        
        logger.info(
            f"Analysis job completed in {duration:.2f} seconds. "
            f"Processed {len(new_conversations)} new conversations and "
            f"reprocessed {len(reprocessed_conversations)} conversations."
        )
    except Exception as e:
        logger.error(f"Analysis job failed: {e}")
        
        # Update sync status
        db = get_db()
        sync_status = SyncStatus(
            component="analysis",
            status="failed",
            last_run=datetime.utcnow(),
            details=f"Analysis job failed: {e}",
        )
        db.update_or_create_item(sync_status, component="analysis")
        
        raise AnalysisError(f"Analysis job failed: {e}")