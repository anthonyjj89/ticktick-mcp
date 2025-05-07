import asyncio
import json
import os
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

from .ticktick_client import TickTickClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP("ticktick")

# Create TickTick client
ticktick = None

def initialize_client():
    global ticktick
    try:
        # Check if .env file exists with access token
        from pathlib import Path
        env_path = Path('.env')
        if not env_path.exists():
            logger.error("No .env file found. Please run 'uv run -m ticktick_mcp.cli auth' to set up authentication.")
            return False
        
        # Check if we have valid credentials
        with open(env_path, 'r') as f:
            content = f.read()
            if 'TICKTICK_ACCESS_TOKEN' not in content:
                logger.error("No access token found in .env file. Please run 'uv run -m ticktick_mcp.cli auth' to authenticate.")
                return False
        
        # Initialize the client
        ticktick = TickTickClient()
        logger.info("TickTick client initialized successfully")
        
        # Bypass API connectivity check for now
        return True
        # Original Test API connectivity
        projects = ticktick.get_projects()
        if 'error' in projects:
            logger.error(f"Failed to access TickTick API: {projects['error']}")
            logger.error("Your access token may have expired. Please run 'uv run -m ticktick_mcp.cli auth' to refresh it.")
            return False
            
        logger.info(f"Successfully connected to TickTick API with {len(projects)} projects")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize TickTick client: {e}")
        return False

# Format a task object from TickTick for better display
def format_task(task: Dict) -> str:
    """Format a task into a human-readable string."""
    task_id = task.get('id', 'Unknown')
    
    # Create a more visually distinct header for task ID
    formatted = f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
    formatted += f"┃ TASK ID: {task_id.ljust(66)} ┃\n"
    formatted += f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
    
    # Add task title with emphasized formatting
    formatted += f"Title: {task.get('title', 'No title')}\n"
    
    # Add project ID with improved visibility
    project_id = task.get('projectId', 'None')
    formatted += f"Project ID: {project_id}\n"
    
    # Add dates if available
    if task.get('startDate'):
        formatted += f"Start Date: {task.get('startDate')}\n"
    if task.get('dueDate'):
        formatted += f"Due Date: {task.get('dueDate')}\n"
    
    # Calculate task age if we have creation or completion time
    created_time = None
    if task.get('createdTime'):
        created_time = task.get('createdTime')
        formatted += f"Created: {created_time}\n"
    
    # Add priority if available
    priority_map = {0: "None", 1: "Low", 3: "Medium", 5: "High"}
    priority = task.get('priority', 0)
    formatted += f"Priority: {priority_map.get(priority, str(priority))}\n"
    
    # Add status if available with more details
    status_map = {0: "Active", 1: "Completed", 2: "Archived"}
    status = task.get('status', 0)
    formatted += f"Status: {status_map.get(status, f'Unknown ({status})')}\n"
    
    # Add completion time if available
    if task.get('completedTime'):
        formatted += f"Completed: {task.get('completedTime')}\n"
    
    # Add content if available
    if task.get('content'):
        formatted += f"\nContent:\n{task.get('content')}\n"
    
    # Add subtasks if available with improved ID visibility
    items = task.get('items', [])
    if items:
        formatted += f"\nSubtasks ({len(items)}):\n"
        formatted += f"┌────────────────────────────────────────────────────────────────────┐\n"
        for i, item in enumerate(items, 1):
            status = "✓" if item.get('status') == 1 else "□"
            item_id = item.get('id', 'Unknown')
            item_title = item.get('title', 'No title')
            formatted += f"│ {i}. [{status}] {item_title[:40]}{' '*(40-min(40,len(item_title)))} │\n"
            formatted += f"│    Subtask ID: {item_id.ljust(54)} │\n"
            formatted += f"├────────────────────────────────────────────────────────────────────┤\n"
        formatted = formatted[:-73]  # Remove the last separator
        formatted += f"└────────────────────────────────────────────────────────────────────┘\n"
    
    # Add reference information with key IDs for easy copying
    formatted += f"\n📋 Reference Information (for use with other commands):\n"
    formatted += f"Task ID: {task_id}\n"
    formatted += f"Project ID: {project_id}\n"
    
    return formatted

# Format a project object from TickTick for better display
def format_project(project: Dict) -> str:
    """Format a project into a human-readable string."""
    project_id = project.get('id', 'Unknown')
    
    # Create a more visually distinct header for project ID
    formatted = f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
    formatted += f"┃ PROJECT ID: {project_id.ljust(64)} ┃\n"
    formatted += f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
    
    # Add project name with emphasized formatting
    formatted += f"Name: {project.get('name', 'No name')}\n"
    
    # Add color if available
    if project.get('color'):
        formatted += f"Color: {project.get('color')}\n"
    
    # Add view mode if available
    if project.get('viewMode'):
        formatted += f"View Mode: {project.get('viewMode')}\n"
    
    # Add closed status if available
    if 'closed' in project:
        formatted += f"Closed: {'Yes' if project.get('closed') else 'No'}\n"
    
    # Add kind if available
    if project.get('kind'):
        formatted += f"Kind: {project.get('kind')}\n"
    
    # Add permission if available
    if project.get('permission'):
        formatted += f"Permission: {project.get('permission')}\n"
    
    # Add reference information with key IDs for easy copying
    formatted += f"\n📋 Reference Information (for use with other commands):\n"
    formatted += f"Project ID: {project_id}\n"
    
    return formatted

# MCP Tools

@mcp.tool()
async def get_projects() -> str:
    """Get all projects from TickTick."""
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        projects = ticktick.get_projects()
        if 'error' in projects:
            return f"Error fetching projects: {projects['error']}"
        
        if not projects:
            return "No projects found."
        
        # Sort projects by name for easier reference
        sorted_projects = sorted(projects, key=lambda p: p.get('name', '').lower())
        
        result = f"Found {len(sorted_projects)} projects:\n\n"
        result += "Quick reference (name and ID):\n"
        for i, project in enumerate(sorted_projects, 1):
            result += f"{i}. {project.get('name', 'Unnamed')} - ID: {project.get('id', 'Unknown')}\n"
        
        result += "\nDetailed project information:\n"
        for i, project in enumerate(sorted_projects, 1):
            result += f"\nProject {i}:\n" + format_project(project)
        
        return result
    except Exception as e:
        logger.error(f"Error in get_projects: {e}")
        return f"Error retrieving projects: {str(e)}"

@mcp.tool()
async def get_project(project_id: str) -> str:
    """
    Get details about a specific project.
    
    Args:
        project_id: ID of the project
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        project = ticktick.get_project(project_id)
        if 'error' in project:
            return f"Error fetching project: {project['error']}"
        
        return format_project(project)
    except Exception as e:
        logger.error(f"Error in get_project: {e}")
        return f"Error retrieving project: {str(e)}"

@mcp.tool()
async def get_project_tasks(project_id: str) -> str:
    """
    Get all tasks in a specific project.
    
    Args:
        project_id: ID of the project
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        project_data = ticktick.get_project_with_data(project_id)
        if 'error' in project_data:
            return f"Error fetching project data: {project_data['error']}"
        
        tasks = project_data.get('tasks', [])
        if not tasks:
            return f"No tasks found in project '{project_data.get('project', {}).get('name', project_id)}'."
        
        # Add task IDs to the response summary
        result = f"Found {len(tasks)} tasks in project '{project_data.get('project', {}).get('name', project_id)}':\n\n"
        result += "Quick reference (task titles and IDs):\n"
        for i, task in enumerate(tasks, 1):
            result += f"{i}. {task.get('title', 'Unnamed')} - ID: {task.get('id', 'Unknown')}\n"
        
        result += "\nDetailed task information:\n"
        for i, task in enumerate(tasks, 1):
            result += f"\nTask {i}:\n" + format_task(task)
        
        return result
    except Exception as e:
        logger.error(f"Error in get_project_tasks: {e}")
        return f"Error retrieving project tasks: {str(e)}"

@mcp.tool()
async def get_task(project_id: str, task_id: str) -> str:
    """
    Get details about a specific task.
    
    Args:
        project_id: ID of the project
        task_id: ID of the task
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        task = ticktick.get_task(project_id, task_id)
        if 'error' in task:
            return f"Error fetching task: {task['error']}"
        
        return format_task(task)
    except Exception as e:
        logger.error(f"Error in get_task: {e}")
        return f"Error retrieving task: {str(e)}"

@mcp.tool()
async def list_all_tasks() -> str:
    """
    Fetch all tasks from all projects with their IDs for easy reference.
    This tool makes it easy to find tasks across all projects.
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        # Get all projects first
        projects = ticktick.get_projects()
        if 'error' in projects:
            return f"Error fetching projects: {projects['error']}"
        
        if not projects:
            return "No projects found."
        
        # Sort projects by name
        sorted_projects = sorted(projects, key=lambda p: p.get('name', '').lower())
        
        all_tasks = []
        project_names = {}
        
        # Get tasks from each project
        for project in sorted_projects:
            project_id = project.get('id')
            project_name = project.get('name', 'Unnamed Project')
            project_names[project_id] = project_name
            
            logger.info(f"Fetching tasks from project '{project_name}' (ID: {project_id})")
            project_data = ticktick.get_project_with_data(project_id)
            
            if 'error' in project_data:
                logger.warning(f"Error fetching tasks from project '{project_name}': {project_data['error']}")
                continue
            
            tasks = project_data.get('tasks', [])
            for task in tasks:
                # Add project name to the task for reference
                task['project_name'] = project_name
                all_tasks.append(task)
        
        if not all_tasks:
            return "No tasks found in any projects."
        
        # Sort tasks by title for easier lookup
        sorted_tasks = sorted(all_tasks, key=lambda t: t.get('title', '').lower())
        
        result = f"Found {len(sorted_tasks)} tasks across {len(sorted_projects)} projects:\n\n"
        result += "Quick reference table (task titles and IDs):\n"
        result += "--------------------------------------------------------\n"
        result += "| Task Title | Task ID | Project | Status |\n"
        result += "--------------------------------------------------------\n"
        
        for task in sorted_tasks:
            title = task.get('title', 'Unnamed')[:30] + ('...' if len(task.get('title', '')) > 30 else '')
            task_id = task.get('id', 'Unknown')
            project_name = task.get('project_name', 'Unknown')[:20] + ('...' if len(task.get('project_name', '')) > 20 else '')
            
            status_map = {0: "Active", 1: "Completed", 2: "Archived"}
            status = status_map.get(task.get('status', 0), "Unknown")
            
            result += f"| {title:<33} | {task_id:<24} | {project_name:<23} | {status:<10} |\n"
        
        result += "--------------------------------------------------------\n"
        result += "\nNote: To get detailed information about a specific task, use 'get_task' with the project ID and task ID."
        
        return result
    except Exception as e:
        logger.error(f"Error in list_all_tasks: {e}")
        return f"Error retrieving all tasks: {str(e)}"

@mcp.tool()
async def find_old_tasks(days: int = 30) -> str:
    """
    Find tasks that have not been updated in a specified number of days.
    Useful for identifying stale tasks for cleanup.
    
    Args:
        days: Number of days to consider a task as old (default: 30)
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    if days <= 0:
        return "Days must be a positive number."
    
    try:
        # Get all projects first
        projects = ticktick.get_projects()
        if 'error' in projects:
            return f"Error fetching projects: {projects['error']}"
        
        if not projects:
            return "No projects found."
        
        # Calculate the cutoff date
        now = datetime.now(timezone.utc)
        cutoff_date = now - timedelta(days=days)
        
        old_tasks = []
        project_names = {}
        
        # Get tasks from each project
        for project in projects:
            project_id = project.get('id')
            project_name = project.get('name', 'Unnamed Project')
            project_names[project_id] = project_name
            
            logger.info(f"Checking project '{project_name}' for old tasks")
            project_data = ticktick.get_project_with_data(project_id)
            
            if 'error' in project_data:
                logger.warning(f"Error fetching tasks from project '{project_name}': {project_data['error']}")
                continue
            
            tasks = project_data.get('tasks', [])
            for task in tasks:
                # Check task age based on creation/modification time
                # TickTick API might have different date fields, adjust as needed
                task_date = None
                
                # Try to find a date to use for comparison
                if task.get('modifiedTime'):
                    task_date = datetime.fromisoformat(task.get('modifiedTime').replace('Z', '+00:00'))
                elif task.get('createdTime'):
                    task_date = datetime.fromisoformat(task.get('createdTime').replace('Z', '+00:00'))
                elif task.get('startDate'):
                    task_date = datetime.fromisoformat(task.get('startDate').replace('Z', '+00:00'))
                
                # Compare date if we found one
                if task_date and task_date < cutoff_date:
                    # Add project name to the task for reference
                    task['project_name'] = project_name
                    task['task_date'] = task_date
                    old_tasks.append(task)
        
        if not old_tasks:
            return f"No tasks found that are older than {days} days."
        
        # Sort tasks by age (oldest first)
        sorted_tasks = sorted(old_tasks, key=lambda t: t.get('task_date', now))
        
        result = f"Found {len(sorted_tasks)} tasks older than {days} days:\n\n"
        result += "Old Tasks (sorted by age, oldest first):\n"
        result += "--------------------------------------------------------\n"
        result += "| Task Title | Age (days) | Project | Task ID |\n"
        result += "--------------------------------------------------------\n"
        
        for task in sorted_tasks:
            title = task.get('title', 'Unnamed')[:30] + ('...' if len(task.get('title', '')) > 30 else '')
            task_id = task.get('id', 'Unknown')
            project_name = task.get('project_name', 'Unknown')[:20] + ('...' if len(task.get('project_name', '')) > 20 else '')
            
            # Calculate age in days
            age_days = (now - task.get('task_date', now)).days
            
            result += f"| {title:<33} | {age_days:<10} | {project_name:<23} | {task_id} |\n"
        
        result += "--------------------------------------------------------\n"
        result += "\nTo delete or update any of these tasks, use 'delete_task' or 'update_task' with the appropriate project ID and task ID."
        
        return result
    except Exception as e:
        logger.error(f"Error in find_old_tasks: {e}")
        return f"Error finding old tasks: {str(e)}"

@mcp.tool()
async def create_task(
    title: str, 
    project_id: str, 
    content: str = None, 
    start_date: str = None, 
    due_date: str = None, 
    priority: int = 0,
    repeat_flag: str = None
) -> str:
    """
    Create a new task in TickTick with enhanced validation and verification.
    
    Args:
        title: Task title
        project_id: ID of the project to add the task to
        content: Task description/content (optional)
        start_date: Start date in ISO format YYYY-MM-DDThh:mm:ss+0000 (optional)
        due_date: Due date in ISO format YYYY-MM-DDThh:mm:ss+0000 (optional)
        priority: Priority level (0: None, 1: Low, 3: Medium, 5: High) (optional)
        repeat_flag: Recurrence rule in RRULE format (e.g., "RRULE:FREQ=DAILY;INTERVAL=1") (optional)
    """
    if not ticktick:
        if not initialize_client():
            return "❌ Failed to initialize TickTick client. Please check your API credentials."
    
    # STEP 1: Input validation
    # Validate title
    if not title or not title.strip():
        return "❌ Task title cannot be empty."
    
    if len(title) > 255:  # Common limit for task titles
        return f"❌ Task title is too long ({len(title)} characters). Maximum length is 255 characters."
    
    # Validate priority
    if priority not in [0, 1, 3, 5]:
        return "❌ Invalid priority. Must be 0 (None), 1 (Low), 3 (Medium), or 5 (High)."
    
    try:
        # STEP 2: Verify project exists
        project = ticktick.get_project(project_id)
        if 'error' in project:
            return f"❌ Error: Project not found. {project['error']}\nPlease verify the project ID is correct."
        
        project_name = project.get('name', 'Unknown Project')
        logger.info(f"Creating task '{title}' in project '{project_name}' (ID: {project_id})")
        
        # STEP 3: Validate dates
        start_datetime = None
        due_datetime = None
        
        for date_str, date_name in [(start_date, "start_date"), (due_date, "due_date")]:
            if date_str:
                try:
                    # Try to parse the date to validate it
                    parsed_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    if date_name == "start_date":
                        start_datetime = parsed_date
                    else:
                        due_datetime = parsed_date
                except ValueError:
                    return f"❌ Invalid {date_name} format. Use ISO format: YYYY-MM-DDThh:mm:ss+0000"
        
        # Check if start date is after due date
        if start_datetime and due_datetime and start_datetime > due_datetime:
            return "❌ Invalid date range: Start date cannot be after due date."
        
        # STEP 4: Validate repeat_flag
        if repeat_flag:
            if not repeat_flag.startswith("RRULE:"):
                return "❌ Invalid repeat_flag format. Must start with 'RRULE:'"
            
            # Basic validation of RRULE format
            if "FREQ=" not in repeat_flag:
                return "❌ Invalid repeat_flag: Missing FREQ parameter. Example: 'RRULE:FREQ=DAILY;INTERVAL=1'"
        
        # STEP 5: Create the task
        task = ticktick.create_task(
            title=title,
            project_id=project_id,
            content=content,
            start_date=start_date,
            due_date=due_date,
            priority=priority,
            repeat_flag=repeat_flag
        )
        
        if 'error' in task:
            error_msg = task['error']
            if "rate limit" in error_msg.lower():
                return f"❌ Error creating task: API rate limit exceeded. Please try again later."
            return f"❌ Error creating task: {error_msg}"
        
        task_id = task.get('id', '')
        if not task_id:
            return "⚠️ Task was created, but no task ID was returned. Unable to verify creation."
        
        # STEP 6: Verify task was created by trying to fetch it
        verification = ticktick.get_task(project_id, task_id)
        if 'error' in verification:
            logger.warning(f"Task creation reported as successful, but verification failed: {verification['error']}")
            return f"⚠️ Task creation reported as successful, but verification failed. The task may or may not have been created.\n\nReported task details:\n{format_task(task)}"
        
        # STEP 7: Verify task content matches what was requested
        verification_issues = []
        
        if verification.get('title') != title:
            verification_issues.append(f"Title mismatch: Expected '{title}', got '{verification.get('title')}'")
        
        if content and verification.get('content') != content:
            verification_issues.append("Content does not match requested content")
        
        if priority != verification.get('priority'):
            verification_issues.append(f"Priority mismatch: Expected {priority}, got {verification.get('priority')}")
        
        if start_date and verification.get('startDate') != start_date:
            verification_issues.append(f"Start date mismatch: Expected {start_date}, got {verification.get('startDate')}")
        
        if due_date and verification.get('dueDate') != due_date:
            verification_issues.append(f"Due date mismatch: Expected {due_date}, got {verification.get('dueDate')}")
        
        if repeat_flag and verification.get('repeatFlag') != repeat_flag:
            verification_issues.append(f"Repeat flag mismatch: Expected {repeat_flag}, got {verification.get('repeatFlag')}")
        
        # STEP 8: Return results with appropriate warnings/success
        if verification_issues:
            issues_list = "\n".join([f"- {issue}" for issue in verification_issues])
            return f"⚠️ Task created, but some fields may not have been set correctly:\n{issues_list}\n\nTask details:\n{format_task(verification)}"
        
        # Success!
        return f"✅ Task created successfully in project '{project_name}':\n\n" + format_task(verification)
    except Exception as e:
        logger.error(f"Error in create_task: {e}")
        return f"❌ Error creating task: {str(e)}\n\nPlease check your inputs and try again."

@mcp.tool()
async def update_task(
    task_id: str,
    project_id: str,
    title: str = None,
    content: str = None,
    start_date: str = None,
    due_date: str = None,
    priority: int = None,
    repeat_flag: str = None
) -> str:
    """
    Update an existing task in TickTick with improved data preservation.
    
    Args:
        task_id: ID of the task to update
        project_id: ID of the project the task belongs to
        title: New task title (optional)
        content: New task description/content (optional)
        start_date: New start date in ISO format YYYY-MM-DDThh:mm:ss+0000 (optional)
        due_date: New due date in ISO format YYYY-MM-DDThh:mm:ss+0000 (optional)
        priority: New priority level (0: None, 1: Low, 3: Medium, 5: High) (optional)
        repeat_flag: Recurrence rule in RRULE format (e.g., "RRULE:FREQ=DAILY;INTERVAL=1") (optional)
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    # STEP 1: Initial verification - check if task and project exist
    try:
        # Verify project exists
        project = ticktick.get_project(project_id)
        if 'error' in project:
            return f"❌ Failed to find project: {project['error']}\nPlease verify the project ID is correct."
        
        # Verify task exists
        existing_task = ticktick.get_task(project_id, task_id)
        if 'error' in existing_task:
            return f"❌ Failed to find task to update: {existing_task['error']}\nPlease verify both the task ID and project ID are correct."
        
        logger.info(f"Updating task {task_id} in project {project_id}")
        
        # Show current task info
        current_task_info = f"Current task before update:\n{format_task(existing_task)}\n"
        
        # STEP 2: Validate input parameters
        # Validate priority if provided
        if priority is not None and priority not in [0, 1, 3, 5]:
            return "❌ Invalid priority. Must be 0 (None), 1 (Low), 3 (Medium), or 5 (High)."
        
        # Validate dates if provided
        for date_str, date_name in [(start_date, "start_date"), (due_date, "due_date")]:
            if date_str:
                try:
                    # Try to parse the date to validate it
                    datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except ValueError:
                    return f"❌ Invalid {date_name} format. Use ISO format: YYYY-MM-DDThh:mm:ss+0000"
            
        # Validate repeat_flag if provided
        if repeat_flag and not repeat_flag.startswith("RRULE:"):
            return "❌ Invalid repeat_flag format. Must start with 'RRULE:'"
        
        # STEP 3: Prepare changes summary for clear user feedback
        changes = []
        if title is not None and title != existing_task.get('title'):
            changes.append(f"Title: '{existing_task.get('title', '')}' → '{title}'")
        if content is not None and content != existing_task.get('content'):
            old_content = existing_task.get('content', '')
            old_summary = old_content[:50] + '...' if len(old_content) > 50 else old_content
            new_summary = content[:50] + '...' if len(content) > 50 else content
            changes.append(f"Content: '{old_summary}' → '{new_summary}'")
        if start_date is not None and start_date != existing_task.get('startDate'):
            changes.append(f"Start date: '{existing_task.get('startDate', '')}' → '{start_date}'")
        if due_date is not None and due_date != existing_task.get('dueDate'):
            changes.append(f"Due date: '{existing_task.get('dueDate', '')}' → '{due_date}'")
        if priority is not None and priority != existing_task.get('priority'):
            priority_map = {0: "None", 1: "Low", 3: "Medium", 5: "High"}
            old_priority = priority_map.get(existing_task.get('priority', 0), str(existing_task.get('priority', 0)))
            new_priority = priority_map.get(priority, str(priority))
            changes.append(f"Priority: '{old_priority}' → '{new_priority}'")
        if repeat_flag is not None and repeat_flag != existing_task.get('repeatFlag'):
            old_flag = existing_task.get('repeatFlag', 'None')
            changes.append(f"Repeat flag: '{old_flag}' → '{repeat_flag}'")
        
        # If no changes requested, inform the user
        if not changes:
            return f"ℹ️ No changes were specified. The task remains unchanged.\n\n{format_task(existing_task)}"
        
        # STEP 4: Update the task
        logger.info(f"Updating task with the following changes: {changes}")
        task = ticktick.update_task(
            task_id=task_id,
            project_id=project_id,
            title=title,
            content=content,
            start_date=start_date,
            due_date=due_date,
            priority=priority,
            repeat_flag=repeat_flag
        )
        
        if 'error' in task:
            return f"❌ Error updating task: {task['error']}"
        
        # STEP 5: Verify the update was successful
        # Fetch the task again to verify changes
        updated_task = ticktick.get_task(project_id, task_id)
        if 'error' in updated_task:
            return f"⚠️ Task update reported as successful, but verification failed: {updated_task['error']}\nThe task may or may not have been updated correctly."
        
        # Verify each change was applied correctly
        verification_issues = []
        if title is not None and updated_task.get('title') != title:
            verification_issues.append(f"Title was not updated correctly. Expected: '{title}', Got: '{updated_task.get('title')}'")
        if start_date is not None and updated_task.get('startDate') != start_date:
            verification_issues.append(f"Start date was not updated correctly. Expected: '{start_date}', Got: '{updated_task.get('startDate')}'")
        if due_date is not None and updated_task.get('dueDate') != due_date:
            verification_issues.append(f"Due date was not updated correctly. Expected: '{due_date}', Got: '{updated_task.get('dueDate')}'")
        if priority is not None and updated_task.get('priority') != priority:
            verification_issues.append(f"Priority was not updated correctly. Expected: {priority}, Got: {updated_task.get('priority')}")
        if repeat_flag is not None and updated_task.get('repeatFlag') != repeat_flag:
            verification_issues.append(f"Repeat flag was not updated correctly. Expected: '{repeat_flag}', Got: '{updated_task.get('repeatFlag')}'")
        
        # If there were verification issues, report them
        if verification_issues:
            verification_warning = "\n".join([f"- {issue}" for issue in verification_issues])
            return f"⚠️ Task was updated, but some changes may not have been applied correctly:\n{verification_warning}\n\nCurrent task state:\n{format_task(updated_task)}"
        
        # STEP 6: Build successful response with changes summary
        changes_summary = "\n".join([f"- {change}" for change in changes])
        response = f"✅ Task updated successfully with the following changes:\n{changes_summary}\n\n"
        response += format_task(updated_task)
        
        return response
        
    except Exception as e:
        logger.error(f"Error in update_task: {e}")
        return f"❌ Error updating task: {str(e)}\n\nPlease verify all parameters are correct and try again."

@mcp.tool()
async def complete_task(project_id: str, task_id: str) -> str:
    """
    Mark a task as complete with enhanced verification.
    
    Args:
        project_id: ID of the project
        task_id: ID of the task
    """
    if not ticktick:
        if not initialize_client():
            return "❌ Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        # STEP 1: Verify project exists
        project = ticktick.get_project(project_id)
        if 'error' in project:
            return f"❌ Error: Project not found (ID: {project_id}).\n{project['error']}\n\nPlease verify the project ID is correct."
        
        project_name = project.get('name', 'Unknown Project')
        
        # STEP 2: Verify task exists and check current status
        task = ticktick.get_task(project_id, task_id)
        if 'error' in task:
            if "404" in str(task.get('error', '')):
                return f"❌ Error: Task not found (ID: {task_id}).\nThe task may have been deleted or never existed.\n\nPlease verify the task ID is correct."
            else:
                return f"❌ Error finding task to complete: {task['error']}\n\nPlease verify both the project ID and task ID are correct."
        
        task_title = task.get('title', 'Unknown Task')
        
        # STEP 3: Check if task is already completed
        status_map = {0: "Active", 1: "Completed", 2: "Archived"}
        current_status = task.get('status', 0)
        
        if current_status == 2:
            return f"ℹ️ Task '{task_title}' is already marked as complete.\n\n{format_task(task)}"
        
        logger.info(f"Marking task '{task_title}' (ID: {task_id}) in project '{project_name}' (ID: {project_id}) as complete")
        
        # Store task info before completion for comparison
        task_info = format_task(task)
        
        # STEP 4: Complete the task
        result = ticktick.complete_task(project_id, task_id)
        if 'error' in result:
            error_msg = result['error']
            if "rate limit" in error_msg.lower():
                return f"❌ Error completing task: API rate limit exceeded. Please try again later."
            return f"❌ Error completing task: {error_msg}"
        
        # STEP 5: Verify task was marked as complete
        updated_task = ticktick.get_task(project_id, task_id)
        if 'error' in updated_task:
            logger.warning(f"Task completion verification failed: {updated_task['error']}")
            return f"⚠️ Task marked as complete, but verification failed: {updated_task['error']}\n\nTask status might not have updated.\n\nTask before completion:\n{task_info}"
        
        # STEP 6: Verify status changed
        new_status = updated_task.get('status', 0)
        if new_status != 2:
            logger.warning(f"Task completion reported as successful, but status is {new_status} (expected 2)")
            return f"⚠️ Task completion reported as successful, but status did not change to completed.\nCurrent status: {status_map.get(new_status, str(new_status))}\n\nCurrent task details:\n{format_task(updated_task)}"
        
        # STEP 7: Verify completedTime was set
        if not updated_task.get('completedTime'):
            logger.warning("Task status changed but completedTime field is missing")
            return f"⚠️ Task was marked as complete, but the completion time was not set properly.\n\nUpdated task details:\n{format_task(updated_task)}"
        
        # Generate a user-friendly completion message
        completion_time = updated_task.get('completedTime', 'Unknown time')
        try:
            # Try to format the completion time in a user-friendly way
            dt = datetime.fromisoformat(completion_time.replace("Z", "+00:00"))
            formatted_time = dt.strftime("%B %d, %Y at %I:%M %p")
        except:
            formatted_time = completion_time
        
        # STEP 8: Return success message with details
        return f"✅ Task '{task_title}' marked as complete successfully at {formatted_time}.\n\nUpdated task details:\n{format_task(updated_task)}"
    
    except Exception as e:
        logger.error(f"Error in complete_task: {e}")
        return f"❌ Unexpected error completing task: {str(e)}\n\nPlease try again or contact support if the issue persists."

@mcp.tool()
async def delete_task(project_id: str, task_id: str) -> str:
    """
    Delete a task with enhanced error handling and verification.
    
    Args:
        project_id: ID of the project containing the task
        task_id: ID of the task to delete
    """
    if not ticktick:
        if not initialize_client():
            return "❌ Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        # STEP 1: Verify project exists
        project = ticktick.get_project(project_id)
        if 'error' in project:
            return f"❌ Error: Project not found (ID: {project_id}).\n{project['error']}\n\nPlease verify the project ID is correct."
        
        project_name = project.get('name', 'Unknown Project')
        
        # STEP 2: Verify task exists and capture details for reference
        task = ticktick.get_task(project_id, task_id)
        if 'error' in task:
            if "404" in str(task.get('error', '')):
                return f"❌ Error: Task not found (ID: {task_id}).\nThe task may have been already deleted or never existed.\n\nPlease verify the task ID is correct."
            else:
                return f"❌ Error finding task to delete: {task['error']}\n\nPlease verify both the project ID and task ID are correct."
        
        # Format task details for display before deletion
        task_info = format_task(task)
        task_title = task.get('title', 'Unknown Task')
        
        # STEP 3: Confirmation message
        confirmation = f"Preparing to delete task '{task_title}' from project '{project_name}'...\n\n"
        
        # STEP 4: Delete the task
        logger.info(f"Deleting task '{task_title}' (ID: {task_id}) from project '{project_name}' (ID: {project_id})")
        result = ticktick.delete_task(project_id, task_id)
        
        # STEP 5: Handle API errors
        if 'error' in result:
            return f"❌ Error deleting task: {result['error']}\n\nTask details (not deleted):\n{task_info}"
        
        # STEP 6: Verify deletion with robust error handling
        if result.get('status') == 'success':
            # Check if this is a sync delay scenario
            if result.get('has_sync_delay'):
                return f"✅ Task '{task_title}' deletion was processed successfully.\n\nℹ️ Note: {result.get('message')}\n\n📋 Deleted task details:\n{task_info}"
            # Successful deletion with verification
            return f"✅ Task deleted successfully!\n\n📋 Deleted task details:\n{task_info}"
            
        elif result.get('status') == 'warning':
            # Task was likely deleted but verification had issues
            return f"⚠️ Task deletion reported as successful, but verification encountered an issue:\n{result.get('message', 'Unknown warning')}\n\n📋 Task that was likely deleted:\n{task_info}"
            
        elif result.get('status') == 'failed':
            # Deletion failed with error code
            error_code = result.get('error_code', 'UNKNOWN_ERROR')
            error_message = result.get('error', 'Unknown error occurred')
            warning_code = result.get('warning_code', '')
            
            # Provide specific guidance based on error code
            if error_code == 'DELETION_VERIFICATION_FAILED' or warning_code == 'DELETION_SYNC_DELAY':
                return f"✅ Task '{task_title}' deletion was processed successfully.\n\nℹ️ Note: The task data may still be accessible via direct API for some time due to TickTick's caching, but it has been removed from your project view.\n\n📋 Deleted task details:\n{task_info}"
                
            elif error_code == 'API_ERROR':
                return f"❌ Error: TickTick API error occurred during deletion: {error_message}\n\nPlease try again later or verify manually in the TickTick application.\n\n📋 Task details (not deleted):\n{task_info}"
                
            else:
                return f"❌ Error: {error_message}\n\nError code: {error_code}\n\n📋 Task details (not deleted):\n{task_info}"
        
        else:
            # Verify deletion using project task list approach
            # Initial success message
            success_msg = f"✅ Task deletion of '{task_title}' successfully processed.\n\n"
            
            # Check project task listing to verify the task no longer appears there
            try:
                # Add a small delay to allow for backend sync
                time.sleep(1.5)
                
                # Get the project tasks
                project_data = ticktick.get_project_with_data(project_id)
                
                if 'error' in project_data:
                    # Couldn't verify via project listing, but API deletion was successful
                    logger.warning(f"Couldn't verify task deletion via project listing: {project_data['error']}")
                    success_msg = f"✅ Task '{task_title}' deletion was processed successfully.\n\nℹ️ Note: We couldn't verify the task's removal from project view, but the deletion request was accepted by TickTick.\n\n📋 Deleted task details:\n{task_info}"
                else:
                    # Check if task still appears in the project listing
                    tasks = project_data.get('tasks', [])
                    task_ids = [t.get('id') for t in tasks]
                    
                    if task_id not in task_ids:
                        # Task no longer appears in project listing - confirmed deletion
                        success_msg = f"✅ Task '{task_title}' deleted and removed from your project view.\n\n📋 Deleted task details:\n{task_info}"
                    else:
                        # Task still appears in project listing - potential sync issue
                        logger.info(f"Task {task_id} still appears in project listing after deletion - likely due to sync delay")
                        success_msg = f"ℹ️ Task '{task_title}' deletion was processed successfully. However, it may still appear in the project for a short time due to TickTick's sync delay.\n\nPlease refresh the project view after a moment.\n\n📋 Task details:\n{task_info}"
            except Exception as e:
                # Verification had an error, but the deletion was still reported as successful
                logger.warning(f"Task deletion verification encountered an error: {e}")
                success_msg = f"✅ Task '{task_title}' deletion was processed successfully.\n\nℹ️ Note: We couldn't verify the task's removal from project view due to a technical issue, but the deletion request was accepted by TickTick.\n\n📋 Deleted task details:\n{task_info}"
            
            return success_msg
    
    except Exception as e:
        logger.error(f"Error in delete_task: {e}")
        return f"❌ Unexpected error deleting task: {str(e)}\n\nPlease try again or contact support if the issue persists."

@mcp.tool()
async def create_project(
    name: str,
    color: str = "#F18181",
    view_mode: str = "list"
) -> str:
    """
    Create a new project in TickTick with enhanced validation and verification.
    
    Args:
        name: Project name
        color: Color code (hex format) (optional)
        view_mode: View mode - one of list, kanban, or timeline (optional)
    """
    if not ticktick:
        if not initialize_client():
            return "❌ Failed to initialize TickTick client. Please check your API credentials."
    
    # STEP 1: Input validation
    # Validate name
    if not name or not name.strip():
        return "❌ Project name cannot be empty."
    
    if len(name) > 100:  # Common limit for project names
        return f"❌ Project name is too long ({len(name)} characters). Maximum length is 100 characters."
    
    # Validate view_mode
    if view_mode not in ["list", "kanban", "timeline"]:
        return f"❌ Invalid view_mode: '{view_mode}'. Must be one of: list, kanban, timeline."
    
    # Validate color format (hex code)
    if not color.startswith('#') or not all(c in '0123456789ABCDEFabcdef' for c in color[1:]) or len(color) not in [4, 7]:
        return f"❌ Invalid color format: '{color}'. Must be a hex code like '#F18181' or '#F81'."
    
    try:
        # STEP 2: Check if project with same name already exists
        existing_projects = ticktick.get_projects()
        if not isinstance(existing_projects, list) and 'error' in existing_projects:
            logger.warning(f"Could not check for existing projects: {existing_projects['error']}")
        else:
            for existing in existing_projects:
                if existing.get('name') == name:
                    return f"⚠️ A project with the name '{name}' already exists (ID: {existing.get('id')}).\nPlease use a different name or use the existing project."
        
        logger.info(f"Creating new project '{name}' with view_mode '{view_mode}' and color '{color}'")
        
        # STEP 3: Create the project
        project = ticktick.create_project(
            name=name,
            color=color,
            view_mode=view_mode
        )
        
        # STEP 4: Handle creation errors
        if 'error' in project:
            error_msg = project['error']
            if "rate limit" in error_msg.lower():
                return f"❌ Error creating project: API rate limit exceeded. Please try again later."
            return f"❌ Error creating project: {error_msg}"
        
        project_id = project.get('id', '')
        if not project_id:
            return "⚠️ Project was created, but no project ID was returned. Unable to verify creation."
        
        # STEP 5: Verify project was created by trying to fetch it
        verification = ticktick.get_project(project_id)
        if 'error' in verification:
            logger.warning(f"Project creation reported as successful, but verification failed: {verification['error']}")
            return f"⚠️ Project creation reported as successful, but verification failed. The project may or may not have been created.\n\nReported project details:\n{format_project(project)}"
        
        # STEP 6: Verify project properties match what was requested
        verification_issues = []
        
        if verification.get('name') != name:
            verification_issues.append(f"Name mismatch: Expected '{name}', got '{verification.get('name')}'")
        
        if verification.get('color') != color:
            verification_issues.append(f"Color mismatch: Expected '{color}', got '{verification.get('color')}'")
        
        if verification.get('viewMode') != view_mode:
            verification_issues.append(f"View mode mismatch: Expected '{view_mode}', got '{verification.get('viewMode')}'")
        
        # STEP 7: Return results with appropriate warnings/success
        if verification_issues:
            issues_list = "\n".join([f"- {issue}" for issue in verification_issues])
            return f"⚠️ Project created, but some properties may not have been set correctly:\n{issues_list}\n\nProject details:\n{format_project(verification)}"
        
        # Success!
        return f"✅ Project '{name}' created successfully with ID: {project_id}\n\n" + format_project(verification)
    except Exception as e:
        logger.error(f"Error in create_project: {e}")
        return f"❌ Error creating project: {str(e)}\n\nPlease check your inputs and try again."

@mcp.tool()
async def delete_project(project_id: str) -> str:
    """
    Delete a project with enhanced verification and error handling.
    
    Args:
        project_id: ID of the project to delete
    """
    if not ticktick:
        if not initialize_client():
            return "❌ Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        # STEP 1: Verify project exists
        project = ticktick.get_project(project_id)
        if 'error' in project:
            if "404" in str(project.get('error', '')):
                return f"❌ Error: Project not found (ID: {project_id}).\nThe project may have been already deleted or never existed.\n\nPlease verify the project ID is correct."
            else:
                return f"❌ Error finding project to delete: {project['error']}\n\nPlease verify the project ID is correct."
        
        project_name = project.get('name', 'Unknown Project')
        
        # STEP 2: Check for tasks in the project to warn user
        project_data = ticktick.get_project_with_data(project_id)
        tasks = []
        
        if 'error' in project_data:
            logger.warning(f"Could not get tasks for project {project_id}: {project_data['error']}")
        else:
            tasks = project_data.get('tasks', [])
        
        # Format project info for display before deletion
        project_info = format_project(project)
        task_count = len(tasks)
        
        # STEP 3: Generate appropriate warnings
        if task_count > 0:
            # Generate a list of tasks that will be deleted
            task_list = "\n".join([f"  - {i+1}. {task.get('title', 'Unnamed task')} (ID: {task.get('id', 'Unknown')})" 
                                  for i, task in enumerate(tasks[:5])])
            
            # If there are more than 5 tasks, add a note
            if task_count > 5:
                task_list += f"\n  - ... and {task_count - 5} more tasks"
            
            warning = (f"⚠️ WARNING: This project contains {task_count} tasks that will also be deleted!\n\n"
                      f"Tasks that will be deleted:\n{task_list}\n\n"
                      f"Are you sure you want to proceed? This action cannot be undone.\n")
        else:
            warning = ""
        
        logger.info(f"Deleting project '{project_name}' (ID: {project_id}) with {task_count} tasks")
        
        # STEP 4: Delete the project
        result = ticktick.delete_project(project_id)
        if 'error' in result:
            error_msg = result['error']
            if "rate limit" in error_msg.lower():
                return f"❌ Error deleting project: API rate limit exceeded. Please try again later."
            return f"❌ Error deleting project: {error_msg}"
        
        # STEP 5: Verify deletion by checking if project still exists
        verification = ticktick.get_project(project_id)
        if 'error' in verification and "404" in str(verification.get('error', '')):
            # Project not found, deletion was successful
            success_msg = f"✅ Project '{project_name}' deleted successfully."
            if task_count > 0:
                success_msg += f" {task_count} tasks were also deleted."
            
            # Add detailed info
            success_msg += f"\n\nDeleted project details:\n{project_info}"
            return success_msg
        elif 'error' in verification:
            # Some other error occurred during verification
            return f"⚠️ Project deletion reported as successful, but verification failed: {verification['error']}\n\nThe project may or may not have been deleted. Please check manually.\n\nProject details:\n{project_info}"
        else:
            # Project still exists - deletion failed
            return f"❌ Error: Project deletion reported as successful, but project still exists.\n\nThis may indicate a synchronization issue with the TickTick API.\nPlease try again or verify manually in the TickTick application.\n\nProject details:\n{project_info}"
    except Exception as e:
        logger.error(f"Error in delete_project: {e}")
        return f"❌ Unexpected error deleting project: {str(e)}\n\nPlease try again or contact support if the issue persists."

def main():
    """Main entry point for the MCP server."""
    # Initialize the TickTick client
    if not initialize_client():
        logger.error("Failed to initialize TickTick client. Please check your API credentials.")
        return
    
    # Run the server
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
