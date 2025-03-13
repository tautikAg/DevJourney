#!/usr/bin/env python3
"""
Update Notion with Today's Cursor Chat History

This script extracts today's Cursor chat history and updates your Notion database.
It can be run daily (e.g., via a cron job or scheduled task) to keep your development log up to date.
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime
from pathlib import Path


def run_extraction(output_dir=None):
    """Run the extraction script."""
    print("Step 1: Extracting today's Cursor chat history...")
    
    cmd = [sys.executable, "extract_today_chats.py"]
    if output_dir:
        cmd.extend(["--output", output_dir])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("Error during extraction:")
        print(result.stderr)
        return None
    
    # Find the output directory from the output
    output_lines = result.stdout.splitlines()
    notion_data_file = None
    
    for line in output_lines:
        if "Notion data saved to:" in line:
            notion_data_file = line.split("Notion data saved to:")[-1].strip()
            break
    
    print(result.stdout)
    
    return notion_data_file


def run_notion_integration(notion_data_file):
    """Run the Notion integration script."""
    if not notion_data_file:
        print("Error: No Notion data file found.")
        return False
    
    print("\nStep 2: Sending data to Notion...")
    
    cmd = [sys.executable, "notion_integration.py", "--input", notion_data_file]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("Error during Notion integration:")
        print(result.stderr)
        return False
    
    print(result.stdout)
    
    return True


def setup_env_file():
    """Set up the .env file if it doesn't exist."""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("Creating .env file for Notion API credentials...")
        
        notion_api_key = input("Enter your Notion API key: ")
        notion_database_id = input("Enter your Notion database ID: ")
        
        with open(env_file, "w") as f:
            f.write(f"NOTION_API_KEY={notion_api_key}\n")
            f.write(f"NOTION_DATABASE_ID={notion_database_id}\n")
        
        print(".env file created successfully.")
    
    return env_file.exists()


def main():
    parser = argparse.ArgumentParser(description="Update Notion with today's Cursor chat history")
    parser.add_argument("--output", "-o", help="Output directory for extracted data")
    parser.add_argument("--setup", action="store_true", help="Set up the .env file with Notion credentials")
    args = parser.parse_args()
    
    # Set up .env file if requested
    if args.setup:
        if not setup_env_file():
            print("Error setting up .env file.")
            return
    
    # Run the extraction script
    notion_data_file = run_extraction(args.output)
    
    if not notion_data_file:
        print("Extraction failed. Cannot proceed with Notion integration.")
        return
    
    # Run the Notion integration script
    success = run_notion_integration(notion_data_file)
    
    if success:
        print("\nSuccess! Your Notion database has been updated with today's Cursor chat history.")
    else:
        print("\nFailed to update Notion database. Please check the errors above.")


if __name__ == "__main__":
    main() 