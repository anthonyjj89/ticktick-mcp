# TickTick MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for TickTick that enables interacting with your TickTick task management system directly through Claude and other MCP clients.

## Features

- 📋 View all your TickTick projects and tasks
- ✏️ Create new projects and tasks through natural language
- 🔄 Update existing task details (title, content, dates, priority)
- ✅ Mark tasks as complete
- 🗑️ Delete tasks and projects
- 🔁 Create recurring tasks (daily, weekly, monthly, etc.)
- 🔄 Full integration with TickTick's open API
- 🔌 Seamless integration with Claude and other MCP clients

## Recent Enhancement: Recurring Tasks

This fork adds support for creating and updating recurring tasks in TickTick through the MCP server.

### How to Use Recurring Tasks

Set the `repeat_flag` parameter when creating or updating tasks. Examples:

- Daily recurring: `RRULE:FREQ=DAILY;INTERVAL=1`
- Weekly recurring: `RRULE:FREQ=WEEKLY;INTERVAL=1`
- Monthly recurring: `RRULE:FREQ=MONTHLY;INTERVAL=1`
- Every 2 days: `RRULE:FREQ=DAILY;INTERVAL=2`

Example usage in Claude:

```
Create a daily recurring task called "Morning standup" with Medium priority in my Work project, with a due date of tomorrow at 9:00 AM.
```

Note: A start_date or due_date should be set for the recurrence pattern to display correctly in the TickTick interface.

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver
- TickTick account with API access
- TickTick API credentials (Client ID, Client Secret, Access Token)

See the original [README](https://github.com/jacepark12/ticktick-mcp/blob/main/README.md) for full installation and usage instructions.
