#!/usr/bin/env python
"""
DevJourney setup script.

This script sets up the DevJourney application.
"""

import os
import sys
import subprocess
import argparse

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def setup_conda_environment():
    """Set up the conda environment."""
    print("Setting up conda environment...")
    
    # Check if conda is installed
    try:
        subprocess.run(["conda", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Conda is not installed. Please install conda first.")
        sys.exit(1)
    
    # Create the conda environment
    try:
        subprocess.run(
            ["conda", "create", "-p", "./env", "python=3.12", "-y"],
            check=True,
        )
        print("Conda environment created successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to create conda environment: {e}")
        sys.exit(1)
    
    # Activate the conda environment and install dependencies
    try:
        # Install the package in development mode
        subprocess.run(
            ["conda", "run", "-p", "./env", "pip", "install", "-e", ".[dev]"],
            check=True,
        )
        print("Dependencies installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install dependencies: {e}")
        sys.exit(1)


def setup_database():
    """Set up the database."""
    print("Setting up database...")
    
    try:
        # Run the setup command
        subprocess.run(
            ["conda", "run", "-p", "./env", "python", "-m", "devjourney", "setup"],
            check=True,
        )
        print("Database set up successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to set up database: {e}")
        sys.exit(1)


def setup_environment_variables():
    """Set up environment variables."""
    print("Setting up environment variables...")
    
    # Check if .env file exists
    if not os.path.exists(".env"):
        # Copy .env.example to .env
        if os.path.exists(".env.example"):
            with open(".env.example", "r") as example_file:
                with open(".env", "w") as env_file:
                    env_file.write(example_file.read())
            print(".env file created from .env.example.")
        else:
            # Create a new .env file
            with open(".env", "w") as env_file:
                env_file.write("# DevJourney environment variables\n")
                env_file.write("NOTION_API_KEY=\n")
                env_file.write("CLAUDE_API_KEY=\n")
                env_file.write("NOTION_DAILY_LOG_DB_ID=\n")
                env_file.write("NOTION_PROBLEM_SOLUTION_DB_ID=\n")
                env_file.write("NOTION_KNOWLEDGE_BASE_DB_ID=\n")
                env_file.write("NOTION_PROJECT_TRACKING_DB_ID=\n")
            print(".env file created.")
    else:
        print(".env file already exists.")
    
    print("Please edit the .env file to set your API keys and database IDs.")


def main():
    """Main entry point for the setup script."""
    parser = argparse.ArgumentParser(description="DevJourney Setup Script")
    
    # Add arguments
    parser.add_argument("--skip-conda", action="store_true", help="Skip conda environment setup")
    parser.add_argument("--skip-database", action="store_true", help="Skip database setup")
    parser.add_argument("--skip-env", action="store_true", help="Skip environment variables setup")
    
    # Parse arguments
    args = parser.parse_args()
    
    print("Setting up DevJourney...")
    
    # Set up conda environment
    if not args.skip_conda:
        setup_conda_environment()
    
    # Set up environment variables
    if not args.skip_env:
        setup_environment_variables()
    
    # Set up database
    if not args.skip_database:
        setup_database()
    
    print("DevJourney setup completed successfully.")
    print("\nTo activate the conda environment, run:")
    print("  conda activate ./env")
    print("\nTo run DevJourney, run:")
    print("  python -m devjourney <command>")
    print("  or")
    print("  python scripts/devjourney.py <command>")
    print("\nAvailable commands:")
    print("  setup      - Set up the environment")
    print("  extract    - Extract conversations")
    print("  analyze    - Analyze conversations")
    print("  sync       - Sync insights with Notion")
    print("  full-sync  - Run a full sync of all components")
    print("  status     - Get the status of all components")
    print("  watch      - Watch for changes in Cursor chat history")
    print("  process    - Process a specific conversation")


if __name__ == "__main__":
    main() 