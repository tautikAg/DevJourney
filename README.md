# DevJourney

A comprehensive personal progress tracking system that integrates Claude conversations and Cursor chat history into a structured Notion database.

## Overview

DevJourney is a productivity tool designed for developers who want to track their learning progress and technical achievements. It automatically extracts insights from your Claude AI conversations and Cursor chat history, analyzes them, and organizes them into a structured Notion database.

### Key Features

- **Claude Desktop Integration**: Extract conversation history from Claude using the Model Context Protocol (MCP)
- **Cursor Chat History Parsing**: Access and process local Cursor chat history
- **Intelligent Analysis**: Identify problem statements, solutions, technical concepts, and code references
- **Notion Integration**: Sync processed data to a structured Notion database
- **User-Friendly Interface**: Easy setup wizard and configuration dashboard

## Installation

### Prerequisites

- Python 3.12 or higher
- Claude Desktop client
- Cursor IDE
- Notion account with API access

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/devjourney.git
   cd devjourney
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e .
   ```

3. Create a `.env` file based on the provided `.env.example`:
   ```bash
   cp .env.example .env
   ```

4. Edit the `.env` file with your API keys and configuration settings.

5. Run the setup wizard:
   ```bash
   devjourney setup
   ```

## Usage

### Basic Commands

- **Start the service**:
  ```bash
  devjourney start
  ```

- **Configure settings**:
  ```bash
  devjourney config
  ```

- **View sync status**:
  ```bash
  devjourney status
  ```

- **Force a manual sync**:
  ```bash
  devjourney sync
  ```

### Notion Database Structure

The system creates the following structure in your Notion workspace:

1. **Daily Logs**: Daily summaries of your progress and achievements
2. **Problem Solutions**: Detailed problem/solution pairs extracted from conversations
3. **Knowledge Base**: Technical concepts and learnings organized by category
4. **Project Tracking**: Progress tracking organized by project

## Development

### Project Structure

```
devjourney/
├── src/
│   └── devjourney/
│       ├── mcp/           # MCP integration
│       ├── extractors/    # Data extraction from Claude and Cursor
│       ├── analysis/      # NLP and data processing
│       ├── notion/        # Notion API integration
│       ├── ui/            # User interface components
│       └── main.py        # Main application entry point
├── tests/                 # Test suite
├── pyproject.toml         # Project configuration
├── README.md              # This file
└── .env.example           # Example environment variables
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Model Context Protocol (MCP)](https://github.com/anthropics/model-context-protocol) for Claude integration
- [Notion API](https://developers.notion.com/) for database integration
