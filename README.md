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

# Cursor Chat History Exporter

This tool exports Cursor chat history and related data from your local machine. It gathers data from various locations where Cursor stores information and organizes it into a more accessible format.

## Features

- Exports chat editing sessions data
- Exports history data
- Exports GitHub Copilot chat data
- Exports global storage data
- Creates summaries of exported data

## Requirements

- Python 3.6 or higher
- No additional packages required (uses only standard library)

## Installation

1. Download the `export_cursor_data.py` script
2. Make it executable (on Unix-based systems):
   ```bash
   chmod +x export_cursor_data.py
   ```

## Usage

### Basic Usage

Run the script without any arguments to export data to a timestamped directory in the current location:

```bash
python export_cursor_data.py
```

### Specify Output Directory

You can specify an output directory using the `--output` or `-o` flag:

```bash
python export_cursor_data.py --output /path/to/export/directory
```

## What Data is Exported

The script exports the following data:

### 1. Chat Editing Sessions

Located at:
- macOS: `~/Library/Application Support/Cursor/User/workspaceStorage/*/chatEditingSessions/`
- Windows: `%APPDATA%\Cursor\User\workspaceStorage\*\chatEditingSessions\`
- Linux: `~/.config/Cursor/User/workspaceStorage/*/chatEditingSessions/`

This includes:
- `state.json` files containing session metadata
- Contents of the `contents` directories

### 2. History Data

Located at:
- macOS: `~/Library/Application Support/Cursor/User/History/`
- Windows: `%APPDATA%\Cursor\User\History\`
- Linux: `~/.config/Cursor/User\History\`

This includes:
- `entries.json` files
- Individual history entry files

### 3. GitHub Copilot Chat Data

Located at:
- macOS: `~/Library/Application Support/Cursor/User/workspaceStorage/*/GitHub.copilot-chat/`
- Windows: `%APPDATA%\Cursor\User\workspaceStorage\*\GitHub.copilot-chat\`
- Linux: `~/.config/Cursor/User/workspaceStorage/*/GitHub.copilot-chat/`

This includes:
- Previews and metadata of `workspace-chunks.json` files

### 4. Global Storage Data

Located at:
- macOS: `~/Library/Application Support/Cursor/User/globalStorage/`
- Windows: `%APPDATA%\Cursor\User\globalStorage\`
- Linux: `~/.config/Cursor/User/globalStorage/`

This includes:
- `storage.json` file
- Information about SQLite databases
- Other configuration files

## Output Structure

The exported data is organized as follows:

```
cursor_data_export_YYYYMMDD_HHMMSS/
├── chat_sessions/
│   └── [workspace-id]/
│       └── [session-id]/
│           ├── state.json
│           ├── summary.txt
│           └── contents/
├── history/
│   ├── history_summary.txt
│   └── [history-dir]/
│       ├── entries.json
│       └── [entry-files]
├── copilot_chat/
│   └── [workspace-id]/
│       ├── chunks_preview.txt
│       └── metadata.txt
├── global_storage/
│   ├── storage.json
│   ├── database_info.txt
│   └── [other-files]
└── export_summary.txt
```

## Privacy and Security

This script only exports data locally and does not transmit any information over the network. All exported data remains on your machine.

## Limitations

- For large files like `workspace-chunks.json`, only previews and metadata are exported to save space
- SQLite databases are not fully exported, only their structure and metadata

## License

This script is provided as-is under the MIT License.

## Contributing

Feel free to submit issues or pull requests to improve this tool.

# Cursor Chat History Analyzer

This tool analyzes the data exported by the Cursor Chat History Exporter. It helps you make sense of the exported data by providing summaries, statistics, and search capabilities.

## Features

- Analyzes chat sessions data and extracts key information
- Provides statistics on history data
- Examines GitHub Copilot chat data
- Analyzes global storage configuration
- Allows searching for specific text across all exported files

## Requirements

- Python 3.6 or higher
- No additional packages required (uses only standard library)

## Usage

### Basic Usage

Run the script with the path to your exported data directory:

```bash
python analyze_cursor_data.py /path/to/exported/data
```

### Search for Specific Text

You can search for specific text within the exported data using the `--search` or `-s` flag:

```bash
python analyze_cursor_data.py /path/to/exported/data --search "your search term"
```

## Output

The analyzer provides detailed information about:

1. **Chat Sessions**
   - Number of sessions per workspace
   - History items in each session
   - Working set files associated with sessions

2. **History Data**
   - Number of history directories
   - Sample entries with metadata
   - Content previews of history items

3. **GitHub Copilot Chat**
   - Workspace information
   - Metadata and content previews

4. **Global Storage**
   - Configuration settings
   - Workspace folders
   - Database information

5. **Search Results** (when using the search option)
   - File paths containing the search term
   - Context around each match

## Example Output

```
Analyzing Cursor data in: cursor_data_export_20240615_123456

=== Chat Sessions Analysis ===

Workspace: ba411b05b67d1e3e0030b3cdfde37f7e
  Session: c7ce5778-b66e-44e3-812a-21ec3d4a8030
    History Items: 12
    History Item 1:
      id: message-1
      role: user
    Working Set Files: 3
      File 1: file:///Users/username/projects/myproject/src/main.py

Total Chat Sessions: 1

=== History Data Analysis ===

History summary file found. Key statistics:
Total history directories: 5

Directory: -435700d0
Resource: file:///Users/username/projects/myproject/src/main.py
Entries: 8
  Entry 1:
    id: 1Hve.json
    timestamp: 1623456789
    Content Preview: import os
import sys
...

=== GitHub Copilot Chat Analysis ===

Workspace: e2babd2055f5eb8f97c1c14df9733bef
  Metadata:
    Workspace ID: e2babd2055f5eb8f97c1c14df9733bef
    File Size: 23951549 bytes
  Preview Sample:
    {"text":"<div class=\"mw-parser-output\">","embedding":[0.023,...]}...

Total Copilot Chat Workspaces: 1

=== Global Storage Analysis ===

Storage.json contents:
  Top-level keys:
    - telemetry
    - backupWorkspaces

  Workspace folders:
    - file:///Users/username/projects/myproject
    - file:///Users/username/projects/anotherproject

Analysis complete!
```

## Using with the Exporter

For the best experience, use this analyzer with data exported by the Cursor Chat History Exporter:

1. First, export your data:
   ```bash
   python export_cursor_data.py --output cursor_data
   ```

2. Then analyze the exported data:
   ```bash
   python analyze_cursor_data.py cursor_data
   ```

3. Optionally, search for specific terms:
   ```bash
   python analyze_cursor_data.py cursor_data --search "function definition"
   ```
