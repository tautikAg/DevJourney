# DevJourney

A comprehensive personal progress tracking system that integrates daily activities from Claude conversations and Cursor chat history into a structured Notion database.

## Overview

DevJourney automatically extracts insights from your coding conversations with AI assistants and organizes them into a structured knowledge base in Notion. It helps you track your learning progress, technical problems solved, and maintain a searchable history of your development journey.

## Features

- **Data Extraction**: Automatically extracts conversations from Claude and Cursor chat history
- **Intelligent Analysis**: Uses NLP to identify problems, solutions, and key learnings
- **Notion Integration**: Organizes everything into a structured Notion database
- **Local LLM Support**: Uses Ollama with Llama3 model for privacy and offline analysis
- **Rich UI**: Terminal-based UI with real-time service status monitoring
- **Background Services**: Automatic extraction and analysis running in the background
- **Customizable**: Configure categories, sync frequency, and Notion templates

## Installation

```bash
# Clone the repository
git clone https://github.com/tautik/DevJourney.git
cd DevJourney

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## Usage

### Command Line Interface

```bash
# Run the setup wizard
devjourney setup

# Start the application
devjourney start

# Test Notion connection
devjourney notion test

# Set up Notion databases
devjourney notion setup --parent-page-id <your-notion-page-id>

# Sync data to Notion
devjourney notion sync --parent-page-id <your-notion-page-id> --days 7
```

### Running Directly

You can also run the application directly using the run.py script:

```bash
# Run with setup wizard
python run.py --setup

# Run in debug mode
python run.py --debug

# Run normally
python run.py
```

## User Interface

DevJourney features a terminal-based UI built with Rich that provides:

- Real-time status monitoring of all services
- Visual indicators for service health
- Easy-to-use setup wizard for configuration

The UI automatically starts background services for:
- Notion synchronization
- Data extraction from configured sources
- Analysis of extracted conversations

## Notion Integration

DevJourney creates the following databases in your Notion workspace:

- **Daily Summaries**: Daily overview of your development activities
- **Problems & Solutions**: Technical problems you've solved
- **Learnings**: Concepts and knowledge you've gained
- **Code References**: Useful code snippets and references
- **Meeting Notes**: Notes from development meetings

To set up the Notion integration:

1. Create a Notion integration at https://www.notion.so/my-integrations
2. Get your integration token
3. Create a page in Notion and share it with your integration
4. Run `devjourney notion setup --parent-page-id <your-page-id>` or use the setup wizard

## Configuration

DevJourney can be configured through the setup wizard, UI, or by editing the configuration file located at `~/.devjourney/config.json`.

### Configuration Options

```json
{
  "notion": {
    "enabled": true,
    "api_token": "your-notion-api-token",
    "parent_page_id": "your-notion-page-id",
    "sync_interval": 30
  },
  "extractors": {
    "enabled": true,
    "interval": 60,
    "cursor": {
      "enabled": true,
      "history_path": "~/Library/Application Support/Cursor/chat_history.json"
    },
    "claude": {
      "enabled": false,
      "api_key": ""
    }
  },
  "analysis": {
    "enabled": true,
    "interval": 120,
    "llm": {
      "provider": "ollama",
      "model": "llama3",
      "temperature": 0.7,
      "max_tokens": 1000
    }
  }
}
```

## Requirements

- Python 3.12+
- Notion account
- Claude API access (optional)
- Ollama with Llama3 model (recommended for local processing)

## License

MIT

## Author

Created by Tautik Agrahari (tautikagrahari@gmail.com)
