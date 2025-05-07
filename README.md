# TickTick MCP Server

![Version](https://img.shields.io/badge/version-1.5.0-blue)

> Enhanced TickTick integration for Claude with improved task management and robust API support

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for TickTick that enables interacting with your TickTick task management system directly through Claude and other MCP clients.

## Features

- 📋 View all your TickTick projects and tasks with clear ID references
- ✏️ Create new projects and tasks through natural language
- 🔄 Update existing task details with better change tracking and data preservation
- ✅ Mark tasks as complete with verification
- 🗑️ Delete tasks and projects with robust error handling
- 🔍 Find and list all tasks across projects for easy management
- 🧹 Identify old/stale tasks for cleanup
- 🔁 Support for recurring tasks with customizable patterns
- 🔄 Full integration with TickTick's open API
- 🔌 Seamless integration with Claude and other MCP clients

## Recent Enhancements

### Version 1.5.0 (Current)

- **Enhanced Tag Support**: Added `tags` parameter to task creation and update functions for easy tagging
- **Batch Task Creation**: New `create_tasks` function to create multiple tasks in a single operation
- **Smart Tag Handling**: Intelligent tag extraction and preservation during task updates
- **Tag Deduplication**: Automatic handling of duplicate tags for cleaner task titles
- **Batch API Integration**: Support for TickTick's batch endpoints with graceful fallback
- **Detailed Batch Results**: Clear success/failure reporting for batch operations

### Version 1.4.0

- **Improved Task Deletion Verification**: Enhanced verification process using project listing checks to accurately confirm deletions
- **API Sync Delay Handling**: Added detection and appropriate handling of TickTick API sync delays
- **Informational Notices for Sync Issues**: Changed error messages (❌) to informational notices (ℹ️) for sync-related issues
- **Consistent Client-Server Messaging**: Ensured consistent messaging between client and server layers
- **Robust Error Recovery**: Better handling of transient API issues with automatic retries
- **Detailed Task Deletion Feedback**: Added clear success indicators and detailed information about deleted tasks

### Version 1.3.0

- **Enhanced Task ID Visibility**: Redesigned task and project display with visually distinct ID sections
- **Complete Data Preservation**: Fixed update_task method to properly preserve all existing task data
- **Comprehensive Error Handling**: Improved error messages for all API operations
- **Extended Verification**: All CRUD operations now include pre and post-operation verification
- **Informative Error Messages**: API errors now include error codes, helpful descriptions, and resolution hints
- **Rate Limit Handling**: Added specific handling for rate limit errors with retry functionality
- **Detailed Operation Feedback**: All operations now provide clear success/error indicators and detailed reports

### Version 1.2.0

- **Improved Task Identification**: Tasks now prominently display their IDs for easier reference
- **Robust Update/Delete Operations**: Better error handling and verification for all CRUD operations
- **Task Lookup Tool**: New `list_all_tasks` function to quickly find task IDs across all projects
- **Task Cleanup Tool**: New `find_old_tasks` function to identify stale tasks for maintenance
- **Enhanced Error Messages**: More informative error responses for troubleshooting
- **Verification Steps**: All operations now include verification to ensure success
- **Better API Integration**: Improved error handling and response validation

### Version 1.1.0

- Added support for recurring tasks with customizable patterns

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver
- TickTick account with API access
- TickTick API credentials (Client ID, Client Secret, Access Token)

## Installation

1. **Clone this repository**:
   ```bash
   git clone https://github.com/anthonyjj89/ticktick-mcp.git
   cd ticktick-mcp
   ```

2. **Install with uv**:
   ```bash
   # Install uv if you don't have it already
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Create a virtual environment
   uv venv

   # Activate the virtual environment
   # On macOS/Linux:
   source .venv/bin/activate
   # On Windows:
   .venv\Scripts\activate

   # Install the package
   uv pip install -e .
   ```

3. **Authenticate with TickTick**:
   ```bash
   # Run the authentication flow
   uv run -m ticktick_mcp.cli auth
   ```

   This will:
   - Ask for your TickTick Client ID and Client Secret
   - Open a browser window for you to log in to TickTick
   - Automatically save your access tokens to a `.env` file

4. **Test your configuration**:
   ```bash
   uv run test_server.py
   ```
   This will verify that your TickTick credentials are working correctly.

## Authentication with TickTick

This server uses OAuth2 to authenticate with TickTick. The setup process is straightforward:

1. Register your application at the [TickTick Developer Center](https://developer.ticktick.com/manage)
   - Set the redirect URI to `http://localhost:8000/callback`
   - Note your Client ID and Client Secret

2. Run the authentication command:
   ```bash
   uv run -m ticktick_mcp.cli auth
   ```

3. Follow the prompts to enter your Client ID and Client Secret

4. A browser window will open for you to authorize the application with your TickTick account

5. After authorizing, you'll be redirected back to the application, and your access tokens will be automatically saved to the `.env` file

The server handles token refresh automatically, so you won't need to reauthenticate unless you revoke access or delete your `.env` file.

## Usage with Claude for Desktop

1. Install [Claude for Desktop](https://claude.ai/download)
2. Edit your Claude for Desktop configuration file:

   **macOS**:
   ```bash
   nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

   **Windows**:
   ```bash
   notepad %APPDATA%\Claude\claude_desktop_config.json
   ```

3. Add the TickTick MCP server configuration, using absolute paths:
   ```json
   {
      "mcpServers": {
         "ticktick": {
            "command": "<absolute path to uv>",
            "args": ["run", "--directory", "<absolute path to ticktick-mcp directory>", "-m", "ticktick_mcp.cli", "run"]
         }
      }
   }
   ```

4. Restart Claude for Desktop

Once connected, you'll see the TickTick MCP server tools available in Claude, indicated by the 🔨 (tools) icon.

## Available MCP Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_projects` | List all your TickTick projects | None |
| `get_project` | Get details about a specific project | `project_id` |
| `get_project_tasks` | List all tasks in a project | `project_id` |
| `get_task` | Get details about a specific task | `project_id`, `task_id` |
| `list_all_tasks` | List all tasks across all projects | None |
| `find_old_tasks` | Find tasks that haven't been updated | `days` (default: 30) |
| `create_task` | Create a new task | `title`, `project_id`, `content` (optional), `start_date` (optional), `due_date` (optional), `priority` (optional), `repeat_flag` (optional), `tags` (optional) |
| `create_tasks` | Create multiple tasks at once | `tasks` (list of task dictionaries) |
| `update_task` | Update an existing task | `task_id`, `project_id`, `title` (optional), `content` (optional), `start_date` (optional), `due_date` (optional), `priority` (optional), `repeat_flag` (optional), `tags` (optional) |
| `complete_task` | Mark a task as complete | `project_id`, `task_id` |
| `delete_task` | Delete a task | `project_id`, `task_id` |
| `create_project` | Create a new project | `name`, `color` (optional), `view_mode` (optional) |
| `delete_project` | Delete a project | `project_id` |

## Enhanced Error Handling and Verification

Version 1.4.0 includes significant improvements to error handling and verification throughout the application, especially for task deletion operations:

### Improved Error Messages

All error messages now follow a consistent format with:
- Clear visual indicators (❌ for errors, ⚠️ for warnings, ✅ for success)
- Specific error codes to help identify issues
- Detailed descriptions of what went wrong
- Suggestions for resolution when possible

Example error message:
```
❌ Error: Project not found (ID: 6226ff9877acee87727fxyz).
The project may have been deleted or never existed.

Please verify the project ID is correct.
```

### Comprehensive Verification

All CRUD operations now include multiple verification steps:

1. **Pre-operation verification**:
   - Validate all input parameters
   - Check that referenced resources exist
   - Ensure inputs conform to TickTick API requirements

2. **Post-operation verification**:
   - Verify operations were successful by retrieving updated resources
   - Compare actual results with expected results
   - Provide detailed feedback on any discrepancies

3. **Enhanced data preservation**:
   - Task updates now preserve all existing data not explicitly changed
   - Automatic field retention ensures no data is lost during partial updates

### API Robustness Improvements

- **Rate limit handling**: Automatic detection of rate limits with helpful feedback
- **Timeout handling**: Better handling of API timeouts with detailed error messages
- **Retry mechanisms**: Automatic retry for transient errors
- **Resource validation**: Thorough validation of resources before operations

### Task Deletion Verification Improvements

The TickTick API has a unique behavior where deleted tasks may still be accessible via direct lookup for some time after deletion due to caching or sync delays. Version 1.4.0 includes specialized handling for this:

- **Multiple verification methods**: Uses both direct task lookup and project task listing to verify deletions
- **Sync delay detection**: Identifies when a task appears to exist due to API caching but is actually deleted
- **Informational notices**: Provides clear informational notices (ℹ️) instead of errors when sync delays occur
- **Verification delay**: Adds a small delay before verification to allow backend synchronization
- **Clear success indicators**: Shows ✅ success indicators with detailed information about the deleted task

## New Tools

### Task Management and Discovery

#### `list_all_tasks`
This tool fetches all tasks from all projects and displays them in a readable format with their IDs for easy reference. It's particularly useful when you need to quickly find a task but don't remember which project it's in.

Example prompt:
```
Show me all my tasks across all projects
```

#### `find_old_tasks`
This tool helps identify tasks that haven't been updated in a while, making it easier to clean up stale tasks. You can specify the number of days to consider a task "old".

Example prompt:
```
Find tasks that haven't been updated in the last 60 days
```

## Example Prompts for Claude

Here are some example prompts to use with Claude after connecting the TickTick MCP server:

### Basic Operations
- "Show me all my TickTick projects"
- "List all tasks in my personal project"
- "Show me all tasks across all projects so I can find task IDs"
- "Find tasks that haven't been updated in the last 30 days"
- "Mark the task with ID '61234567891a1b2c3d4e5f6' as complete"
- "Create a new project called 'Vacation Planning' with a blue color"
- "Delete task '81234567891a1b2c3d4e5f8' from project '91234567891a1b2c3d4e5f9'"

### Task Creation and Update
- "Create a new task called 'Finish MCP server documentation' in my work project with high priority"
- "Update the content of task '71234567891a1b2c3d4e5f7' to include meeting notes"
- "Create a weekly recurring task called 'Team Meeting' in my work project due every Monday at 10:00 AM"

### Using Tags (Version 1.5.0+)
- "Create a task called 'Draft report' in my work project with tags 'priority', 'deadline', and 'report'"
- "Update task '12345' in project '67890' to add tags 'follow-up' and 'meeting'"
- "Create a task to 'Review marketing materials' with the tag 'marketing' in my work project"

### Batch Task Creation (Version 1.5.0+)
- "Create these tasks in my personal project:
   1. Buy groceries (tag: shopping)
   2. Call doctor for appointment (tags: health, priority)
   3. Pay utility bills (tags: finance, monthly)"
   
- "Add the following tasks to my work project:
   - Prepare slides for presentation (due next Friday, high priority, tags: presentation, meeting)
   - Send weekly report (recurring weekly on Friday, tags: report, regular)
   - Schedule team lunch (tags: team, social)"

## Using Tags

Version 1.5.0 introduces enhanced tag support that makes it easy to add tags to your tasks. Tags in TickTick are represented as hashtags (e.g., #work, #personal) and help with task organization and filtering.

### Adding Tags to Tasks

You can add tags when creating or updating tasks using the `tags` parameter:

```
Create a task called "Prepare presentation" in my work project with high priority and tags ["work", "meeting", "important"]
```

This will create a task with the hashtags #work, #meeting, and #important appended to the title.

### Smart Tag Handling During Updates

When updating a task, the system intelligently handles tags:

1. If you provide both a new title and tags, the new title and tags will completely replace the existing ones
2. If you provide only tags (no title), the existing non-tag portion of the title is preserved, and only the tags are updated
3. Duplicate tags are automatically removed

Example:
```
Update the task with ID "12345" in project "67890" with tags ["priority", "deadline"]
```

### Batch Task Creation

Version 1.5.0 also adds support for creating multiple tasks at once through the `create_tasks` function:

```
Create these tasks in my project:
- "Buy groceries" with tags ["shopping", "errands"]
- "Schedule dentist" with tags ["health", "appointment"]
- "Review report" with priority 5
```

The `create_tasks` function accepts a list of task dictionaries and creates them all in a single operation, which is more efficient than creating them one by one. Each task dictionary should contain:

- `title`: Task title (required)
- `project_id`: ID of the project (required)
- Other fields like `content`, `start_date`, `due_date`, `priority`, `tags`, and `repeat_flag` are optional

The response includes details about successful and failed tasks, making it easy to identify any issues.

## Using Recurring Tasks

This MCP supports creating and updating recurring tasks in TickTick through the `repeat_flag` parameter. The recurrence pattern follows the iCalendar RRULE format.

Example recurrence patterns:
- Daily: `RRULE:FREQ=DAILY;INTERVAL=1`
- Weekly: `RRULE:FREQ=WEEKLY;INTERVAL=1`
- Monthly: `RRULE:FREQ=MONTHLY;INTERVAL=1`
- Every 2 days: `RRULE:FREQ=DAILY;INTERVAL=2`
- Every 2 weeks: `RRULE:FREQ=WEEKLY;INTERVAL=2`
- Every Monday, Wednesday, Friday: `RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR`
- First day of month: `RRULE:FREQ=MONTHLY;BYMONTHDAY=1`

To create a recurring task, simply add the `repeat_flag` parameter when creating or updating a task:

```
Create a weekly recurring task called "Status Meeting" in my project with medium priority, due every Monday at 9:00 AM
```

Note: A start_date or due_date should be set for the recurrence pattern to display correctly in the TickTick interface.

## Development

### Project Structure

```
tickTick-mcp/
├── .env.template          # Template for environment variables
├── README.md              # Project documentation
├── requirements.txt       # Project dependencies
├── setup.py               # Package setup file
├── test_server.py         # Test script for server configuration
└── ticktick_mcp/          # Main package
    ├── __init__.py        # Package initialization
    ├── authenticate.py    # OAuth authentication utility
    ├── cli.py             # Command-line interface
    └── src/               # Source code
        ├── __init__.py    # Module initialization
        ├── auth.py        # OAuth authentication implementation
        ├── server.py      # MCP server implementation
        └── ticktick_client.py  # TickTick API client
```

### Authentication Flow

The project implements a complete OAuth 2.0 flow for TickTick:

1. **Initial Setup**: User provides their TickTick API Client ID and Secret
2. **Browser Authorization**: User is redirected to TickTick to grant access
3. **Token Reception**: A local server receives the OAuth callback with the authorization code
4. **Token Exchange**: The code is exchanged for access and refresh tokens
5. **Token Storage**: Tokens are securely stored in the local `.env` file
6. **Token Refresh**: The client automatically refreshes the access token when it expires

This simplifies the user experience by handling the entire OAuth flow programmatically.

### Error Handling and Verification

The improved MCP includes enhanced error handling and verification steps for all operations:

1. **Pre-operation Verification**: Before performing operations like update or delete, the system verifies that the target exists
2. **Detailed Error Messages**: Error responses include more detailed information to assist troubleshooting
3. **Post-operation Verification**: After operations are performed, the system verifies that the changes were applied correctly
4. **Change Tracking**: For update operations, the system shows which fields were changed and their old/new values

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
