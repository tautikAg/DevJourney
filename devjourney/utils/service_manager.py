"""
Service manager for DevJourney.
Handles starting, stopping, and checking status of background services.
"""
import logging
import threading
import time
from typing import Dict, Any, List, Optional
import importlib

from devjourney.config.settings import config

logger = logging.getLogger(__name__)

# Global registry of running services
_services = {}
_service_threads = {}


def start_services() -> None:
    """Start all configured background services."""
    logger.info("Starting DevJourney services")
    
    # Start Notion sync if enabled
    if config.get("notion", {}).get("enabled", False):
        start_notion_sync()
    
    # Start extractors if enabled
    if config.get("extractors", {}).get("enabled", False):
        start_extractors()
    
    # Start analysis service if enabled
    if config.get("analysis", {}).get("enabled", False):
        start_analysis_service()
    
    logger.info("All services started")


def stop_services() -> None:
    """Stop all running services."""
    logger.info("Stopping all services")
    
    # Set stop flag for all services
    for service_name in _services:
        _services[service_name]["running"] = False
    
    # Wait for all threads to complete
    for thread_name, thread in _service_threads.items():
        if thread.is_alive():
            logger.info(f"Waiting for {thread_name} to stop...")
            thread.join(timeout=5)
    
    logger.info("All services stopped")


def check_status() -> Dict[str, Dict[str, Any]]:
    """Check the status of all services.
    
    Returns:
        Dict with service names as keys and status info as values
    """
    status = {}
    
    # Add Notion sync status
    status["Notion Sync"] = {
        "running": _services.get("notion_sync", {}).get("running", False),
        "details": f"Last sync: {_services.get('notion_sync', {}).get('last_sync', 'Never')}"
    }
    
    # Add extractors status
    status["Extractors"] = {
        "running": _services.get("extractors", {}).get("running", False),
        "details": f"Active: {_services.get('extractors', {}).get('active_count', 0)}"
    }
    
    # Add analysis service status
    status["Analysis"] = {
        "running": _services.get("analysis", {}).get("running", False),
        "details": f"Last run: {_services.get('analysis', {}).get('last_run', 'Never')}"
    }
    
    return status


def start_notion_sync() -> None:
    """Start the Notion sync service in a background thread."""
    if _services.get("notion_sync", {}).get("running", False):
        logger.info("Notion sync already running")
        return
    
    logger.info("Starting Notion sync service")
    
    # Initialize service state
    _services["notion_sync"] = {
        "running": True,
        "last_sync": "Never",
        "error_count": 0
    }
    
    # Start in a background thread
    thread = threading.Thread(
        target=_notion_sync_worker,
        name="notion_sync_thread",
        daemon=True
    )
    thread.start()
    
    # Store thread reference
    _service_threads["notion_sync"] = thread
    
    logger.info("Notion sync service started")


def _notion_sync_worker() -> None:
    """Worker function for Notion sync service."""
    try:
        # Import here to avoid circular imports
        from devjourney.notion.sync import sync_to_notion
        
        # Get sync interval from config (default to 30 minutes)
        sync_interval = config.get("notion", {}).get("sync_interval", 30) * 60
        
        while _services["notion_sync"]["running"]:
            try:
                # Run sync
                logger.info("Running Notion sync")
                sync_to_notion()
                
                # Update last sync time
                _services["notion_sync"]["last_sync"] = time.strftime("%Y-%m-%d %H:%M:%S")
                
                # Sleep until next sync
                logger.info(f"Notion sync completed, next sync in {sync_interval/60} minutes")
                
                # Check stop flag periodically during sleep
                for _ in range(int(sync_interval / 10)):
                    if not _services["notion_sync"]["running"]:
                        break
                    time.sleep(10)
                    
            except Exception as e:
                logger.exception("Error in Notion sync")
                _services["notion_sync"]["error_count"] += 1
                
                # Sleep for a bit before retrying
                time.sleep(60)
    
    except Exception as e:
        logger.exception("Fatal error in Notion sync worker")
        _services["notion_sync"]["running"] = False


def start_extractors() -> None:
    """Start the extractors service in a background thread."""
    if _services.get("extractors", {}).get("running", False):
        logger.info("Extractors already running")
        return
    
    logger.info("Starting extractors service")
    
    # Initialize service state
    _services["extractors"] = {
        "running": True,
        "active_count": 0,
        "last_run": "Never",
        "error_count": 0
    }
    
    # Start in a background thread
    thread = threading.Thread(
        target=_extractors_worker,
        name="extractors_thread",
        daemon=True
    )
    thread.start()
    
    # Store thread reference
    _service_threads["extractors"] = thread
    
    logger.info("Extractors service started")


def _extractors_worker() -> None:
    """Worker function for extractors service."""
    try:
        # Import here to avoid circular imports
        from devjourney.extractors.factory import create_extractor
        
        # Get extraction interval from config (default to 60 minutes)
        extraction_interval = config.get("extractors", {}).get("interval", 60) * 60
        
        while _services["extractors"]["running"]:
            try:
                # Get enabled extractors from config
                enabled_extractors = []
                extractor_config = config.get("extractors", {})
                
                if extractor_config.get("cursor", {}).get("enabled", False):
                    enabled_extractors.append("cursor")
                
                if extractor_config.get("claude", {}).get("enabled", False):
                    enabled_extractors.append("claude")
                
                # Update active count
                _services["extractors"]["active_count"] = len(enabled_extractors)
                
                # Run each enabled extractor
                for source_type in enabled_extractors:
                    logger.info(f"Running extractor for {source_type}")
                    extractor = create_extractor(source_type)
                    extractor.extract()
                
                # Update last run time
                _services["extractors"]["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
                
                # Sleep until next extraction
                logger.info(f"Extraction completed, next run in {extraction_interval/60} minutes")
                
                # Check stop flag periodically during sleep
                for _ in range(int(extraction_interval / 10)):
                    if not _services["extractors"]["running"]:
                        break
                    time.sleep(10)
                    
            except Exception as e:
                logger.exception("Error in extractors service")
                _services["extractors"]["error_count"] += 1
                
                # Sleep for a bit before retrying
                time.sleep(60)
    
    except Exception as e:
        logger.exception("Fatal error in extractors worker")
        _services["extractors"]["running"] = False


def start_analysis_service() -> None:
    """Start the analysis service in a background thread."""
    if _services.get("analysis", {}).get("running", False):
        logger.info("Analysis service already running")
        return
    
    logger.info("Starting analysis service")
    
    # Initialize service state
    _services["analysis"] = {
        "running": True,
        "last_run": "Never",
        "error_count": 0
    }
    
    # Start in a background thread
    thread = threading.Thread(
        target=_analysis_worker,
        name="analysis_thread",
        daemon=True
    )
    thread.start()
    
    # Store thread reference
    _service_threads["analysis"] = thread
    
    logger.info("Analysis service started")


def _analysis_worker() -> None:
    """Worker function for analysis service."""
    try:
        # Import here to avoid circular imports
        from devjourney.analyzers.analyzer import ConversationAnalyzer, analyze_recent_conversations
        
        # Get analysis interval from config (default to 120 minutes)
        analysis_interval = config.get("analysis", {}).get("interval", 120) * 60
        
        while _services["analysis"]["running"]:
            try:
                # Run analysis
                logger.info("Running conversation analysis")
                analyze_recent_conversations()
                
                # Update last run time
                _services["analysis"]["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
                
                # Sleep until next analysis
                logger.info(f"Analysis completed, next run in {analysis_interval/60} minutes")
                
                # Check stop flag periodically during sleep
                for _ in range(int(analysis_interval / 10)):
                    if not _services["analysis"]["running"]:
                        break
                    time.sleep(10)
                    
            except Exception as e:
                logger.exception("Error in analysis service")
                _services["analysis"]["error_count"] += 1
                
                # Sleep for a bit before retrying
                time.sleep(60)
    
    except Exception as e:
        logger.exception("Fatal error in analysis worker")
        _services["analysis"]["running"] = False 