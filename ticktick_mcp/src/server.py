import asyncio
import json
import os
import logging
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
    # Make the task ID clearly visible at the top
    formatted = f"===== TASK ID: {task.get('id', 'Unknown')} =====\n"
    formatted += f"Title: {task.get('title', 'No title')}\n"
    
    # Add project ID
    formatted += f"Project ID: {task.get('projectId', 'None')}\n"
    
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
    
    # Add subtasks if available
    items = task.get('items', [])
    if items:
        formatted += f"\nSubtasks ({len(items)}):\n"
        for i, item in enumerate(items, 1):
            status = "✓" if item.get('status') == 1 else "□"
            item_id = item.get('id', 'Unknown')
            formatted += f"{i}. [{status}] {item.get('title', 'No title')} (ID: {item_id})\n"
    
    # Add footer with task ID for easy reference
    formatted += f"\n===== END OF TASK {task.get('id', 'Unknown')} =====\n"
    
    return formatted

# Format a project object from TickTick for better display
def format_project(project: Dict) -> str:
    """Format a project into a human-readable string."""
    # Make the project ID clearly visible
    formatted = f"===== PROJECT ID: {project.get('id', 'Unknown')} =====\n"
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
    
    # Add footer with project ID for easy reference
    formatted += f"\n===== END OF PROJECT {project.get('id', 'Unknown')} =====\n"
    
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
    Create a new task in TickTick.
    
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
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    # Validate priority
    if priority not in [0, 1, 3, 5]:
        return "Invalid priority. Must be 0 (None), 1 (Low), 3 (Medium), or 5 (High)."
    
    try:
        # Verify the project exists first
        project = ticktick.get_project(project_id)
        if 'error' in project:
            return f"Error: Project not found. {project['error']}"
        
        # Validate dates if provided
        for date_str, date_name in [(start_date, "start_date"), (due_date, "due_date")]:
            if date_str:
                try:
                    # Try to parse the date to validate it
                    datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except ValueError:
                    return f"Invalid {date_name} format. Use ISO format: YYYY-MM-DDThh:mm:ss+0000"
        
        # Validate repeat_flag if provided
        if repeat_flag and not repeat_flag.startswith("RRULE:"):
            return "Invalid repeat_flag format. Must start with 'RRULE:'"
        
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
            return f"Error creating task: {task['error']}"
        
        # Verify task was created by trying to fetch it
        verification = ticktick.get_task(project_id, task.get('id', ''))
        if 'error' in verification:
            logger.warning(f"Task creation reported as successful, but verification failed: {verification['error']}")
            return f"Task creation reported as successful, but verification failed. The task may or may not have been created.\n\nReported task details:\n{format_task(task)}"
        
        return f"Task created successfully:\n\n" + format_task(task)
    except Exception as e:
        logger.error(f"Error in create_task: {e}")
        return f"Error creating task: {str(e)}"

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
    Update an existing task in TickTick.
    
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
    
    # First, verify task exists
    try:
        existing_task = ticktick.get_task(project_id, task_id)
        if 'error' in existing_task:
            return f"Failed to find task to update: {existing_task['error']}"
        
        logger.info(f"Updating task {task_id} in project {project_id}")
        
        # Show current task info
        current_task_info = f"Current task before update:\n{format_task(existing_task)}\n"
        
        # Validate priority if provided
        if priority is not None and priority not in [0, 1, 3, 5]:
            return "Invalid priority. Must be 0 (None), 1 (Low), 3 (Medium), or 5 (High)."
        
        # Validate dates if provided
        for date_str, date_name in [(start_date, "start_date"), (due_date, "due_date")]:
            if date_str:
                try:
                    # Try to parse the date to validate it
                    datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except ValueError:
                    return f"Invalid {date_name} format. Use ISO format: YYYY-MM-DDThh:mm:ss+0000"
            
        # Validate repeat_flag if provided
        if repeat_flag and not repeat_flag.startswith("RRULE:"):
            return "Invalid repeat_flag format. Must start with 'RRULE:'"
        
        # Prepare changes summary
        changes = []
        if title is not None and title != existing_task.get('title'):
            changes.append(f"Title: '{existing_task.get('title', '')}' → '{title}'")
        if content is not None and content != existing_task.get('content'):
            changes.append("Content updated")
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
            changes.append(f"Repeat flag: '{existing_task.get('repeatFlag', '')}' → '{repeat_flag}'")
        
        # Update the task
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
            return f"Error updating task: {task['error']}"
        
        # Verify update by comparing with before
        if not changes:
            return f"No changes were made to the task.\n\n{format_task(task)}"
        
        # Build response with changes summary
        changes_summary = "\n".join([f"- {change}" for change in changes])
        response = f"Task updated successfully with the following changes:\n{changes_summary}\n\n"
        response += format_task(task)
        
        return response
        
    except Exception as e:
        logger.error(f"Error in update_task: {e}")
        return f"Error updating task: {str(e)}"

@mcp.tool()
async def complete_task(project_id: str, task_id: str) -> str:
    """
    Mark a task as complete.
    
    Args:
        project_id: ID of the project
        task_id: ID of the task
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        # First, verify task exists and show what's being completed
        task = ticktick.get_task(project_id, task_id)
        if 'error' in task:
            return f"Error finding task to complete: {task['error']}"
        
        if task.get('status') == 2:
            return f"Task is already marked as complete.\n\n{format_task(task)}"
        
        # Task info before completion
        task_info = format_task(task)
        
        # Complete the task
        result = ticktick.complete_task(project_id, task_id)
        if 'error' in result:
            return f"Error completing task: {result['error']}"
        
        # Verify task was marked as complete
        updated_task = ticktick.get_task(project_id, task_id)
        if 'error' in updated_task:
            logger.warning(f"Task completion verification failed: {updated_task['error']}")
            return f"Task marked as complete, but verification failed. Task status might not have updated.\n\nTask before completion:\n{task_info}"
        
        # Check if status changed
        if updated_task.get('status') != 2:
            logger.warning(f"Task completion reported as successful, but status is still {updated_task.get('status')}")
            return f"Task completion reported as successful, but status did not change to completed.\n\nCurrent task status:\n{format_task(updated_task)}"
        
        return f"Task marked as complete successfully.\n\nUpdated task details:\n{format_task(updated_task)}"
    except Exception as e:
        logger.error(f"Error in complete_task: {e}")
        return f"Error completing task: {str(e)}"

@mcp.tool()
async def delete_task(project_id: str, task_id: str) -> str:
    """
    Delete a task.
    
    Args:
        project_id: ID of the project
        task_id: ID of the task
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        # First, get the task to verify it exists and show what's being deleted
        task = ticktick.get_task(project_id, task_id)
        if 'error' in task:
            return f"Error finding task to delete: {task['error']}"
        
        # Show task details before deletion
        task_info = format_task(task)
        
        # Delete the task
        result = ticktick.delete_task(project_id, task_id)
        if 'error' in result:
            return f"Error deleting task: {result['error']}"
        
        # Verify deletion by checking if task still exists
        verification = ticktick.get_task(project_id, task_id)
        if 'error' in verification and "404" in str(verification.get('error', '')):
            # Task not found, deletion was successful
            return f"Task deleted successfully:\n\nDeleted task details:\n{task_info}"
        elif 'error' in verification:
            # Some other error occurred
            return f"Task deletion reported as successful, but verification failed: {verification['error']}\n\nDeleted task details:\n{task_info}"
        else:
            # Task still exists
            return f"Error: Task deletion reported as successful, but task still exists.\n\nTask details:\n{task_info}"
    except Exception as e:
        logger.error(f"Error in delete_task: {e}")
        return f"Error deleting task: {str(e)}"

@mcp.tool()
async def create_project(
    name: str,
    color: str = "#F18181",
    view_mode: str = "list"
) -> str:
    """
    Create a new project in TickTick.
    
    Args:
        name: Project name
        color: Color code (hex format) (optional)
        view_mode: View mode - one of list, kanban, or timeline (optional)
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    # Validate view_mode
    if view_mode not in ["list", "kanban", "timeline"]:
        return "Invalid view_mode. Must be one of: list, kanban, timeline."
    
    try:
        project = ticktick.create_project(
            name=name,
            color=color,
            view_mode=view_mode
        )
        
        if 'error' in project:
            return f"Error creating project: {project['error']}"
        
        return f"Project created successfully:\n\n" + format_project(project)
    except Exception as e:
        logger.error(f"Error in create_project: {e}")
        return f"Error creating project: {str(e)}"

@mcp.tool()
async def delete_project(project_id: str) -> str:
    """
    Delete a project.
    
    Args:
        project_id: ID of the project
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        # First, verify project exists and show what's being deleted
        project = ticktick.get_project(project_id)
        if 'error' in project:
            return f"Error finding project to delete: {project['error']}"
        
        # Get tasks in the project before deletion for reference
        project_data = ticktick.get_project_with_data(project_id)
        tasks = project_data.get('tasks', []) if 'error' not in project_data else []
        
        # Show project details before deletion
        project_info = format_project(project)
        task_count = len(tasks)
        
        # Warning about tasks that will be deleted
        warning = f"WARNING: This project contains {task_count} tasks that will also be deleted.\n\n" if task_count > 0 else ""
        
        # Delete the project
        result = ticktick.delete_project(project_id)
        if 'error' in result:
            return f"Error deleting project: {result['error']}"
        
        # Verify deletion by checking if project still exists
        verification = ticktick.get_project(project_id)
        if 'error' in verification and "404" in str(verification.get('error', '')):
            # Project not found, deletion was successful
            return f"Project deleted successfully:\n\n{warning}Deleted project details:\n{project_info}"
        elif 'error' in verification:
            # Some other error occurred
            return f"Project deletion reported as successful, but verification failed: {verification['error']}\n\n{warning}Deleted project details:\n{project_info}"
        else:
            # Project still exists
            return f"Error: Project deletion reported as successful, but project still exists.\n\nProject details:\n{project_info}"
    except Exception as e:
        logger.error(f"Error in delete_project: {e}")
        return f"Error deleting project: {str(e)}"

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
