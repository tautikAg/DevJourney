# Cursor to Notion Integration

This set of scripts extracts your daily Cursor chat history and updates your Notion database with it, helping you track your development progress and activities.

## Features

- Extracts today's chat sessions from Cursor
- Identifies files you've worked on
- Captures code snippets and conversations
- Creates or updates a daily entry in your Notion database
- Formats everything nicely in Notion with headings, code blocks, and more

## Requirements

- Python 3.6 or higher
- Notion account with API access
- Cursor IDE

## Setup

1. **Install required packages**:
   ```bash
   pip install notion-client python-dotenv
   ```

2. **Set up Notion API access**:
   - Create an integration in the [Notion Integrations page](https://www.notion.so/my-integrations)
   - Copy the "Internal Integration Token" (this is your API key)
   - Create a database in Notion with at least these properties:
     - Title (title property)
     - Date (date property)
   - Share your database with the integration you created
   - Copy the database ID from the URL (it's the part after the workspace name and before the question mark)

3. **Configure the scripts**:
   ```bash
   python update_notion_with_cursor.py --setup
   ```
   This will prompt you for your Notion API key and database ID and create a `.env` file.

## Usage

### Basic Usage

Run the script to extract today's Cursor chat history and update your Notion database:

```bash
python update_notion_with_cursor.py
```

### Specify Output Directory

You can specify an output directory for the extracted data:

```bash
python update_notion_with_cursor.py --output /path/to/output/directory
```

### Automate Daily Updates

#### On macOS/Linux:

Add a cron job to run the script daily:

```bash
crontab -e
```

Add this line to run it every day at 6 PM:

```
0 18 * * * cd /path/to/script/directory && python update_notion_with_cursor.py
```

#### On Windows:

Use Task Scheduler to run the script daily.

## How It Works

The integration consists of three main scripts:

1. **extract_today_chats.py**: Extracts today's chat history from Cursor and formats it for Notion.
2. **notion_integration.py**: Sends the formatted data to Notion.
3. **update_notion_with_cursor.py**: Wrapper script that runs both of the above in sequence.

The data is organized in your Notion database as follows:

- **Daily entries**: Each day gets its own page in your database
- **Chat sessions**: Conversations with Cursor are grouped by session
- **Edited files**: A list of files you worked on
- **Code snippets**: Important code snippets extracted from your history

## Customization

You can customize the Notion page format by modifying the formatting functions in `notion_integration.py`:

- `format_chat_sessions_for_notion()`
- `format_edited_files_for_notion()`
- `format_code_snippets_for_notion()`

## Troubleshooting

- **Script fails to find Cursor data**: Make sure Cursor is installed and you've used it recently.
- **Notion API errors**: Verify your API key and database ID are correct in the `.env` file.
- **No data found for today**: The script only extracts chat history from the current day.

## Privacy

These scripts run locally on your machine and only send data to Notion. No data is sent to any other servers. 