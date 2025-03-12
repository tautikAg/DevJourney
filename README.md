# DevJourney

A comprehensive personal progress tracking system that integrates daily activities from Claude conversations and Cursor chat history into a structured Notion database.

## Overview

DevJourney automatically extracts insights from your coding conversations with AI assistants and organizes them into a structured knowledge base in Notion. It helps you track your learning progress, technical problems solved, and maintain a searchable history of your development journey.

## Features

- **Data Extraction**: Automatically extracts conversations from Claude and Cursor chat history
- **Intelligent Analysis**: Uses NLP to identify problems, solutions, and key learnings
- **Notion Integration**: Organizes everything into a structured Notion database
- **Local LLM Support**: Uses Ollama with Deepseek-r1 model for privacy and offline analysis
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

```bash
# Run the setup wizard
devjourney setup

# Start the application
devjourney start
```

## Configuration

DevJourney can be configured through the UI or by editing the configuration file located at `~/.devjourney/config.yaml`.

## Requirements

- Python 3.8+
- Notion account
- Claude API access (optional)
- Ollama with Deepseek-r1 model (recommended for local processing)

## License

MIT

## Author

Created by Tautik Agrahari (tautikagrahari@gmail.com)
