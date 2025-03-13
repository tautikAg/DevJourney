#!/usr/bin/env python3
"""
Simple script to test the Notion API connection.
"""

import os
import sys
import asyncio
import httpx
from dotenv import load_dotenv

async def test_notion_api():
    """Test the Notion API connection directly."""
    print("Testing Notion API connection...")
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get the API key from environment
    api_key = os.getenv("NOTION_API_KEY")
    
    if not api_key:
        print("ERROR: Notion API key is not set in the .env file.")
        return False
    
    print(f"Using API key: {api_key[:4]}...{api_key[-4:]}")
    
    # Make a direct request to the Notion API
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.notion.com/v1/users/me",
                headers=headers,
                timeout=30.0,
            )
            
            print(f"Response status code: {response.status_code}")
            
            if response.status_code == 200:
                user_data = response.json()
                print(f"Successfully connected to Notion API as user: {user_data.get('name', 'Unknown')}")
                print(f"User ID: {user_data.get('id', 'Unknown')}")
                print(f"Bot ID: {user_data.get('bot', {}).get('id', 'Unknown')}")
                return True
            else:
                try:
                    error_data = response.json()
                    print(f"Notion API error: {response.status_code} - {error_data.get('message', 'Unknown error')}")
                except Exception:
                    print(f"Notion API error: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"Failed to connect to Notion API: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_notion_api())
    if success:
        print("Notion API connection test successful!")
        sys.exit(0)
    else:
        print("Notion API connection test failed.")
        sys.exit(1) 