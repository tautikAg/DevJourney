#!/usr/bin/env python3
"""
DevJourney - Personal Development Progress Tracking System

This script serves as the main entry point for the DevJourney application.
It sets up logging, processes command-line arguments, and starts the application.
"""
import argparse
import logging
import os
import sys
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import DevJourney modules
from devjourney.config.settings import config
from devjourney.ui.app import start_app
from devjourney.ui.setup_wizard import run_setup_wizard


def setup_logging():
    """Set up logging configuration."""
    log_level = getattr(logging, config["app"]["log_level"])
    
    # Create logs directory if it doesn't exist
    log_dir = Path(os.path.expanduser(config["app"]["data_dir"])) / "logs"
    log_dir.mkdir(exist_ok=True, parents=True)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "devjourney.log"),
            logging.StreamHandler()
        ]
    )
    
    # Set third-party loggers to WARNING level
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="DevJourney - Personal Development Progress Tracking")
    
    # Add arguments
    parser.add_argument(
        "--setup", 
        action="store_true", 
        help="Run the setup wizard"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug mode"
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the application."""
    # Parse command-line arguments
    args = parse_args()
    
    # Set debug mode if requested
    if args.debug:
        config["app"]["log_level"] = "DEBUG"
    
    # Set up logging
    setup_logging()
    
    # Get logger
    logger = logging.getLogger(__name__)
    logger.info("Starting DevJourney")
    
    # Run setup wizard if requested or if first run
    config_file = Path(os.path.expanduser(config["app"]["data_dir"])) / "config.json"
    if args.setup or not config_file.exists():
        logger.info("Running setup wizard")
        run_setup_wizard()
    
    # Start the application
    start_app()


if __name__ == "__main__":
    main() 