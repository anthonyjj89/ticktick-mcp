import os
import json
import base64
import requests
import logging
import time
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Tuple

# Set up logging
logger = logging.getLogger(__name__)

class TickTickClient:
    """
    Client for the TickTick API using OAuth2 authentication.
    """
    
    def __init__(self):
        load_dotenv()
        self.client_id = os.getenv("TICKTICK_CLIENT_ID")
        self.client_secret = os.getenv("TICKTICK_CLIENT_SECRET")
        self.access_token = os.getenv("TICKTICK_ACCESS_TOKEN")
        self.refresh_token = os.getenv("TICKTICK_REFRESH_TOKEN")
        
        if not self.access_token:
            raise ValueError("TICKTICK_ACCESS_TOKEN environment variable is not set. "
                            "Please run 'uv run -m ticktick_mcp.authenticate' to set up your credentials.")
            
        self.base_url = "https://api.ticktick.com/open/v1"
        self.token_url = "https://ticktick.com/oauth/token"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def _refresh_access_token(self) -> bool:
        """
        Refresh the access token using the refresh token.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.refresh_token:
            logger.warning("No refresh token available. Cannot refresh access token.")
            return False
            
        if not self.client_id or not self.client_secret:
            logger.warning("Client ID or Client Secret missing. Cannot refresh access token.")
            return False
            
        # Prepare the token request
        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        
        # Prepare Basic Auth credentials
        auth_str = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_str.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            # Send the token request
            response = requests.post(self.token_url, data=token_data, headers=headers)
            response.raise_for_status()
            
            # Parse the response
            tokens = response.json()
            
            # Update the tokens
            self.access_token = tokens.get('access_token')
            if 'refresh_token' in tokens:
                self.refresh_token = tokens.get('refresh_token')
                
            # Update the headers
            self.headers["Authorization"] = f"Bearer {self.access_token}"
            
            # Save the tokens to the .env file
            self._save_tokens_to_env(tokens)
            
            logger.info("Access token refreshed successfully.")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error refreshing access token: {e}")
            return False
    
    def _save_tokens_to_env(self, tokens: Dict[str, str]) -> None:
        """
        Save the tokens to the .env file.
        
        Args:
            tokens: A dictionary containing the access_token and optionally refresh_token
        """
        # Load existing .env file content
        env_path = Path('.env')
        env_content = {}
        
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_content[key] = value
        
        # Update with new tokens
        env_content["TICKTICK_ACCESS_TOKEN"] = tokens.get('access_token', '')
        if 'refresh_token' in tokens:
            env_content["TICKTICK_REFRESH_TOKEN"] = tokens.get('refresh_token', '')
        
        # Make sure client credentials are saved as well
        if self.client_id and "TICKTICK_CLIENT_ID" not in env_content:
            env_content["TICKTICK_CLIENT_ID"] = self.client_id
        if self.client_secret and "TICKTICK_CLIENT_SECRET" not in env_content:
            env_content["TICKTICK_CLIENT_SECRET"] = self.client_secret
        
        # Write back to .env file
        with open(env_path, 'w') as f:
            for key, value in env_content.items():
                f.write(f"{key}={value}\n")
        
        logger.debug("Tokens saved to .env file")
    
    def _make_request(self, method: str, endpoint: str, data=None, timeout: int = 30, retry_on_error: bool = True) -> Dict:
        """
        Makes a request to the TickTick API with enhanced error handling.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            data: Request data (for POST, PUT)
            timeout: Request timeout in seconds (default: 30)
            retry_on_error: Whether to retry on specific transient errors (default: True)
        
        Returns:
            API response as a dictionary with consistent error format
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            # Log request details for debugging
            logger.debug(f"Making {method} request to {url}")
            if data:
                logger.debug(f"Request data: {json.dumps(data, indent=2)}")
            
            # Request options for all requests
            request_options = {
                "headers": self.headers,
                "timeout": timeout
            }
            
            # Make the request
            if method == "GET":
                response = requests.get(url, **request_options)
            elif method == "POST":
                response = requests.post(url, json=data, **request_options)
            elif method == "DELETE":
                response = requests.delete(url, **request_options)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # CASE 1: Authentication issues (401)
            if response.status_code == 401:
                logger.info("Access token expired. Attempting to refresh...")
                
                # Try to refresh the access token
                if self._refresh_access_token():
                    logger.info("Token refreshed. Retrying request...")
                    # Update headers with new token
                    request_options["headers"] = self.headers
                    
                    # Retry the request with the new token
                    if method == "GET":
                        response = requests.get(url, **request_options)
                    elif method == "POST":
                        response = requests.post(url, json=data, **request_options)
                    elif method == "DELETE":
                        response = requests.delete(url, **request_options)
                else:
                    logger.error("Failed to refresh token. Authentication required.")
                    return {
                        "error": "Authentication failed. Your access token is expired or invalid.",
                        "error_code": "AUTH_FAILED",
                        "status": "failed",
                        "resolution": "Please run 'uv run -m ticktick_mcp.cli auth' to reauthenticate."
                    }
            
            # CASE 2: Resource not found (404)
            if response.status_code == 404:
                error_detail = self._extract_error_details(response)
                resource_type = "task" if "/task/" in endpoint else "project" if "/project/" in endpoint else "resource"
                
                logger.warning(f"{resource_type.capitalize()} not found: {endpoint} - {error_detail}")
                return {
                    "error": f"{resource_type.capitalize()} not found. It may have been deleted or never existed.",
                    "error_code": "NOT_FOUND",
                    "status": "failed",
                    "http_status": 404,
                    "details": error_detail
                }
            
            # CASE 3: Rate limiting (429)
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After', '60')
                error_detail = self._extract_error_details(response)
                
                logger.warning(f"Rate limit exceeded. Retry after {retry_after} seconds.")
                return {
                    "error": f"TickTick API rate limit exceeded. Please try again after {retry_after} seconds.",
                    "error_code": "RATE_LIMITED",
                    "status": "failed",
                    "http_status": 429,
                    "retry_after": retry_after,
                    "details": error_detail
                }
            
            # CASE 4: Server errors (5xx)
            if response.status_code >= 500:
                error_detail = self._extract_error_details(response)
                
                # Determine if this is a transient error we might want to retry
                is_transient = response.status_code in (502, 503, 504)
                
                if is_transient and retry_on_error:
                    logger.warning(f"Transient server error ({response.status_code}). Retrying request...")
                    # Wait briefly before retrying
                    time.sleep(1)
                    # Retry with retry_on_error=False to prevent infinite retries
                    return self._make_request(method, endpoint, data, timeout, False)
                
                logger.error(f"Server error: {response.status_code} - {error_detail}")
                return {
                    "error": f"TickTick server error (HTTP {response.status_code}). Please try again later.",
                    "error_code": "SERVER_ERROR",
                    "status": "failed",
                    "http_status": response.status_code,
                    "details": error_detail,
                    "is_transient": is_transient
                }
            
            # CASE 5: Other client errors (4xx)
            if response.status_code >= 400:
                error_detail = self._extract_error_details(response)
                
                # Map common status codes to more descriptive error codes
                error_code_map = {
                    400: "BAD_REQUEST",
                    403: "FORBIDDEN",
                    405: "METHOD_NOT_ALLOWED",
                    409: "CONFLICT",
                    413: "PAYLOAD_TOO_LARGE",
                    415: "UNSUPPORTED_MEDIA_TYPE",
                    422: "VALIDATION_ERROR"
                }
                
                error_code = error_code_map.get(response.status_code, f"CLIENT_ERROR_{response.status_code}")
                
                logger.error(f"Client error: {response.status_code} - {error_detail}")
                return {
                    "error": f"Request error: {error_detail}",
                    "error_code": error_code,
                    "status": "failed",
                    "http_status": response.status_code,
                    "details": error_detail
                }
            
            # CASE 6: Success with no content (204)
            if response.status_code == 204:
                return {
                    "success": True,
                    "status": "success",
                    "message": "Operation completed successfully",
                    "http_status": 204
                }
            
            # CASE 7: Success with content (200)
            # Parse and validate the response
            try:
                result = response.json()
                logger.debug(f"API response: {json.dumps(result, indent=2)}")
                
                # Add standard success fields if they're not already present
                if isinstance(result, dict) and "status" not in result:
                    result["status"] = "success"
                
                return result
            except json.JSONDecodeError:
                if response.text:
                    logger.warning(f"Received non-JSON response: {response.text[:100]}...")
                    return {
                        "error": f"Invalid JSON response from TickTick API",
                        "error_code": "INVALID_RESPONSE_FORMAT",
                        "status": "warning",
                        "http_status": response.status_code,
                        "raw_response": response.text[:1000]  # Limit to 1000 chars
                    }
                
                # Empty response but success status code
                return {
                    "success": True,
                    "status": "success",
                    "message": "Operation completed successfully",
                    "http_status": response.status_code
                }
                
        except requests.exceptions.Timeout as e:
            error_message = f"Request timed out after {timeout} seconds: {str(e)}"
            logger.error(error_message)
            return {
                "error": error_message,
                "error_code": "TIMEOUT",
                "status": "failed",
                "is_transient": True
            }
        except requests.exceptions.ConnectionError as e:
            error_message = f"Connection error: {str(e)}"
            logger.error(error_message)
            return {
                "error": "Unable to connect to TickTick API. Please check your internet connection.",
                "error_code": "CONNECTION_ERROR",
                "status": "failed",
                "is_transient": True,
                "details": str(e)
            }
        except requests.exceptions.RequestException as e:
            error_message = f"API request failed: {str(e)}"
            logger.error(error_message)
            return {
                "error": error_message,
                "error_code": "REQUEST_FAILED",
                "status": "failed",
                "details": str(e)
            }
        except Exception as e:
            error_message = f"Unexpected error during API request: {str(e)}"
            logger.error(error_message)
            return {
                "error": error_message,
                "error_code": "UNEXPECTED_ERROR",
                "status": "failed",
                "details": str(e)
            }
            
    def _extract_error_details(self, response):
        """Extract error details from response object."""
        try:
            # Try to parse as JSON first
            error_detail = response.json()
            if isinstance(error_detail, dict) and 'error' in error_detail:
                return error_detail['error']
            return json.dumps(error_detail)
        except Exception:
            # Fall back to text or status description
            if response.text:
                return response.text
            
            # Map status codes to descriptions
            status_descriptions = {
                400: "Bad Request",
                401: "Unauthorized",
                403: "Forbidden",
                404: "Not Found",
                405: "Method Not Allowed",
                409: "Conflict",
                429: "Too Many Requests",
                500: "Internal Server Error",
                502: "Bad Gateway",
                503: "Service Unavailable",
                504: "Gateway Timeout"
            }
            
            return status_descriptions.get(response.status_code, f"HTTP {response.status_code}")
    
    # Project methods
    def get_projects(self) -> List[Dict]:
        """Gets all projects for the user."""
        result = self._make_request("GET", "/project")
        if isinstance(result, list):
            # Add a visible identifier to each project
            for project in result:
                if 'id' in project and 'name' in project:
                    project['identifier'] = f"{project['name']} (ID: {project['id']})"
        return result
    
    def get_project(self, project_id: str) -> Dict:
        """Gets a specific project by ID."""
        return self._make_request("GET", f"/project/{project_id}")
    
    def get_project_with_data(self, project_id: str) -> Dict:
        """Gets project with tasks and columns."""
        return self._make_request("GET", f"/project/{project_id}/data")
    
    def create_project(self, name: str, color: str = "#F18181", view_mode: str = "list", kind: str = "TASK") -> Dict:
        """Creates a new project."""
        data = {
            "name": name,
            "color": color,
            "viewMode": view_mode,
            "kind": kind
        }
        return self._make_request("POST", "/project", data)
    
    def update_project(self, project_id: str, name: str = None, color: str = None, 
                       view_mode: str = None, kind: str = None) -> Dict:
        """Updates an existing project."""
        data = {}
        if name:
            data["name"] = name
        if color:
            data["color"] = color
        if view_mode:
            data["viewMode"] = view_mode
        if kind:
            data["kind"] = kind
            
        return self._make_request("POST", f"/project/{project_id}", data)
    
    def delete_project(self, project_id: str) -> Dict:
        """Deletes a project."""
        return self._make_request("DELETE", f"/project/{project_id}")
    
    # Task methods
    def get_task(self, project_id: str, task_id: str) -> Dict:
        """Gets a specific task by project ID and task ID."""
        return self._make_request("GET", f"/project/{project_id}/task/{task_id}")
    
    def create_task(self, title: str, project_id: str, content: str = None, 
                   start_date: str = None, due_date: str = None, 
                   priority: int = 0, is_all_day: bool = False, repeat_flag: str = None,
                   tags: list = None) -> Dict:
        """
        Creates a new task with support for tags.
        
        Args:
            title: Task title
            project_id: ID of the project to add the task to
            content: Task description/content (optional)
            start_date: Start date in ISO format (optional)
            due_date: Due date in ISO format (optional)
            priority: Priority level (0: None, 1: Low, 3: Medium, 5: High) (optional)
            is_all_day: Whether the task is an all-day task (optional)
            repeat_flag: Recurrence rule in RRULE format (optional)
            tags: List of tags to add to the task (optional)
        
        Returns:
            Dictionary with task data or error
        """
        # Process tags if provided by appending hashtags to the title
        if tags and isinstance(tags, list) and len(tags) > 0:
            # Format tags with hashtags if they don't already have them
            formatted_tags = [f"#{tag.strip('#')}" for tag in tags]
            tag_string = " ".join(formatted_tags)
            
            # Append tags to the title
            title = f"{title} {tag_string}"
            
            # If original title had tags, this may duplicate them, but TickTick API
            # appears to handle this case by deduplicating tags
            
        data = {
            "title": title,
            "projectId": project_id
        }
        
        if content:
            data["content"] = content
        if start_date:
            data["startDate"] = start_date
        if due_date:
            data["dueDate"] = due_date
        if priority is not None:
            data["priority"] = priority
        if is_all_day is not None:
            data["isAllDay"] = is_all_day
        if repeat_flag:
            data["repeatFlag"] = repeat_flag
            
        return self._make_request("POST", "/task", data)
    
    def update_task(self, task_id: str, project_id: str, title: str = None, 
                   content: str = None, priority: int = None, 
                   start_date: str = None, due_date: str = None,
                   repeat_flag: str = None, tags: list = None) -> Dict:
        """
        Updates an existing task with robust data preservation and tag support.
        
        Args:
            task_id: ID of the task to update
            project_id: ID of the project containing the task
            title: New task title (optional)
            content: New task description/content (optional)
            priority: New priority level (optional)
            start_date: New start date in ISO format (optional)
            due_date: New due date in ISO format (optional)
            repeat_flag: New recurrence rule in RRULE format (optional)
            tags: New list of tags to add to the task (optional)
        
        Returns:
            Dictionary with task data or error
        """
        # First, get the current task to preserve existing data
        try:
            current_task = self.get_task(project_id, task_id)
            if 'error' in current_task:
                return current_task  # Return the error
            
            # Start with a complete copy of the current task data (complete data preservation)
            data = current_task.copy()
            
            # Ensure ID and projectId are always correct
            data["id"] = task_id
            data["projectId"] = project_id
            
            # Handle title and tags
            if title is not None or tags is not None:
                # If we have a new title, use it as the base, otherwise use the current title
                new_title = title if title is not None else current_task.get("title", "")
                
                # Process tags if provided
                if tags and isinstance(tags, list) and len(tags) > 0:
                    # Extract existing tags from the current title
                    existing_tags = []
                    
                    # If we're not changing the title, extract hashtags from current title
                    if title is None and "#" in new_title:
                        # This is a simple extraction that assumes tags are at the end of the title
                        # A more complex implementation might use regex to extract all hashtags
                        words = new_title.split()
                        non_tag_words = []
                        
                        for word in words:
                            if word.startswith("#"):
                                existing_tags.append(word)
                            else:
                                non_tag_words.append(word)
                        
                        # Reconstruct the base title without tags
                        if non_tag_words:
                            new_title = " ".join(non_tag_words)
                    
                    # Format new tags with hashtags
                    formatted_tags = [f"#{tag.strip('#')}" for tag in tags]
                    
                    # Combine with existing tags and deduplicate
                    all_tags = list(set(existing_tags + formatted_tags))
                    tag_string = " ".join(all_tags)
                    
                    # Create new title with tags
                    new_title = f"{new_title} {tag_string}"
                
                # Update the title in the data
                data["title"] = new_title.strip()
            
            # Update other fields if explicitly provided
            if content is not None:
                data["content"] = content
                
            if priority is not None:
                data["priority"] = priority
                
            if start_date is not None:
                data["startDate"] = start_date
                
            if due_date is not None:
                data["dueDate"] = due_date
                
            if repeat_flag is not None:
                data["repeatFlag"] = repeat_flag
            
            # Remove any fields that shouldn't be included in the update request
            # These fields are typically server-managed or read-only
            fields_to_remove = [
                "createdTime", "completedTime", "modifiedTime", 
                "etag", "timeZone", "sortOrder"
            ]
            
            for field in fields_to_remove:
                if field in data:
                    data.pop(field)
            
            # Log the update data for debugging
            logger.debug(f"Updating task {task_id} with preserved data: {json.dumps(data, indent=2)}")
            
            return self._make_request("POST", f"/task/{task_id}", data)
            
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}")
            return {"error": f"Failed to update task: {str(e)}"}
    
    def complete_task(self, project_id: str, task_id: str) -> Dict:
        """Marks a task as complete."""
        return self._make_request("POST", f"/project/{project_id}/task/{task_id}/complete")
    
    def create_tasks(self, tasks: list) -> List[Dict]:
        """
        Create multiple tasks in a single operation.
        
        Args:
            tasks: List of task dictionaries, each containing:
                - title: Task title (required)
                - project_id: ID of the project (required)
                - content: Task description/content (optional)
                - start_date: Start date in ISO format (optional)
                - due_date: Due date in ISO format (optional)
                - priority: Priority level (optional)
                - tags: List of tags (optional)
                - repeat_flag: Recurrence rule (optional)
            
        Returns:
            List of created task objects or error
        """
        try:
            if not tasks or not isinstance(tasks, list):
                return {"error": "Invalid input: tasks must be a non-empty list of task dictionaries", 
                        "error_code": "INVALID_INPUT",
                        "status": "failed"}
            
            # Validate each task has the required fields
            for i, task in enumerate(tasks):
                if not isinstance(task, dict):
                    return {"error": f"Invalid task at position {i}: must be a dictionary", 
                            "error_code": "INVALID_TASK_FORMAT",
                            "status": "failed"}
                if "title" not in task:
                    return {"error": f"Invalid task at position {i}: missing required field 'title'", 
                            "error_code": "MISSING_REQUIRED_FIELD",
                            "status": "failed"}
                if "project_id" not in task:
                    return {"error": f"Invalid task at position {i}: missing required field 'project_id'", 
                            "error_code": "MISSING_REQUIRED_FIELD",
                            "status": "failed"}
            
            # Format tasks for the API
            formatted_tasks = []
            for task in tasks:
                formatted_task = {
                    "title": task["title"],
                    "projectId": task["project_id"]
                }
                
                # Process tags if provided
                if "tags" in task and task["tags"] and isinstance(task["tags"], list):
                    formatted_tags = [f"#{tag.strip('#')}" for tag in task["tags"]]
                    tag_string = " ".join(formatted_tags)
                    formatted_task["title"] = f"{formatted_task['title']} {tag_string}"
                
                # Add optional fields
                if "content" in task and task["content"]:
                    formatted_task["content"] = task["content"]
                    
                if "start_date" in task and task["start_date"]:
                    formatted_task["startDate"] = task["start_date"]
                    
                if "due_date" in task and task["due_date"]:
                    formatted_task["dueDate"] = task["due_date"]
                    
                if "priority" in task:
                    formatted_task["priority"] = task["priority"]
                    
                if "repeat_flag" in task and task["repeat_flag"]:
                    formatted_task["repeatFlag"] = task["repeat_flag"]
                    
                if "is_all_day" in task:
                    formatted_task["isAllDay"] = task["is_all_day"]
                
                formatted_tasks.append(formatted_task)
            
            # Try batch endpoint first
            try:
                batch_data = {"add": formatted_tasks}
                logger.info(f"Attempting batch creation of {len(formatted_tasks)} tasks")
                response = self._make_request("POST", "/batch/task", batch_data)
                
                # If successful, return the created tasks
                if "error" not in response and response.get("status") != "failed":
                    created_tasks = response.get("add", [])
                    logger.info(f"Successfully created {len(created_tasks)} tasks in batch")
                    return {
                        "status": "success",
                        "message": f"Successfully created {len(created_tasks)} tasks in batch",
                        "tasks": created_tasks
                    }
                else:
                    logger.warning(f"Batch task creation failed: {response.get('error', 'Unknown error')}")
                    logger.info("Falling back to individual task creation")
            except Exception as e:
                logger.warning(f"Batch endpoint failed: {str(e)}")
                logger.info("Falling back to individual task creation")
            
            # Fallback to individual creation
            logger.info(f"Creating {len(tasks)} tasks individually")
            results = []
            successful_count = 0
            
            for i, task in enumerate(tasks):
                try:
                    result = self.create_task(
                        title=task["title"],
                        project_id=task["project_id"],
                        content=task.get("content"),
                        start_date=task.get("start_date"),
                        due_date=task.get("due_date"),
                        priority=task.get("priority", 0),
                        is_all_day=task.get("is_all_day", False),
                        repeat_flag=task.get("repeat_flag"),
                        tags=task.get("tags")
                    )
                    
                    if "error" in result:
                        # Add task index for better error reporting
                        result["task_index"] = i
                        result["task_data"] = task
                    else:
                        successful_count += 1
                        
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error creating task at position {i}: {str(e)}")
                    results.append({
                        "error": f"Failed to create task: {str(e)}",
                        "task_index": i,
                        "task_data": task,
                        "status": "failed"
                    })
            
            # Return combined results
            return {
                "status": "partial" if successful_count < len(tasks) else "success",
                "message": f"Created {successful_count} out of {len(tasks)} tasks",
                "tasks": results,
                "successful_count": successful_count,
                "total_count": len(tasks)
            }
            
        except Exception as e:
            logger.error(f"Error in batch task creation: {str(e)}")
            return {
                "error": f"Failed to process batch task creation: {str(e)}",
                "error_code": "BATCH_PROCESSING_ERROR",
                "status": "failed"
            }
    
    def delete_task(self, project_id: str, task_id: str, retry_count: int = 1) -> Dict:
        """
        Deletes a task with enhanced error handling and verification.
        
        Args:
            project_id: ID of the project containing the task
            task_id: ID of the task to delete
            retry_count: Number of retry attempts for transient errors (default: 1)
        
        Returns:
            Dictionary with operation result
        """
        try:
            # Verify project exists first
            project = self.get_project(project_id)
            if 'error' in project:
                error_code = 'PROJECT_NOT_FOUND'
                error_msg = f"Cannot delete task: Project not found - {project['error']}"
                logger.error(error_msg)
                return {
                    "error": error_msg,
                    "error_code": error_code,
                    "status": "failed",
                    "http_status": 404
                }
            
            # Verify task exists before attempting to delete
            task = self.get_task(project_id, task_id)
            if 'error' in task:
                error_code = 'TASK_NOT_FOUND' if "404" in str(task.get('error', '')) else 'TASK_FETCH_ERROR'
                error_msg = f"Cannot delete task: {task['error']}"
                logger.error(error_msg)
                return {
                    "error": error_msg,
                    "error_code": error_code,
                    "status": "failed",
                    "http_status": 404 if error_code == 'TASK_NOT_FOUND' else 400
                }
            
            # Store task details for response
            task_details = {
                "title": task.get('title', 'Unknown'),
                "id": task_id,
                "project_id": project_id,
                "project_name": project.get('name', 'Unknown Project')
            }
            
            # Task exists, proceed with deletion
            logger.info(f"Deleting task '{task.get('title', 'Unknown')}' (ID: {task_id}) from project '{project.get('name', 'Unknown')}' (ID: {project_id})")
            result = self._make_request("DELETE", f"/project/{project_id}/task/{task_id}")
            
            # Handle API errors
            if 'error' in result:
                # If we encounter a recoverable error and have retries left, retry the operation
                recoverable_errors = ["timeout", "rate limit", "server error", "500", "503"]
                if any(err in str(result['error']).lower() for err in recoverable_errors) and retry_count > 0:
                    logger.warning(f"Encountered recoverable error: {result['error']}. Retrying... ({retry_count} attempts left)")
                    return self.delete_task(project_id, task_id, retry_count - 1)
                
                # Not recoverable or out of retries
                logger.error(f"Failed to delete task {task_id}: {result['error']}")
                return {
                    "error": f"API error while deleting task: {result['error']}",
                    "error_code": "API_ERROR",
                    "status": "failed",
                    "task_details": task_details
                }
            
            # Verify deletion was successful by checking if task still exists
            verification = self.get_task(project_id, task_id)
            if 'error' in verification and "404" in str(verification.get('error', '')):
                # Task not found after deletion, this is expected - success!
                logger.info(f"Successfully deleted task {task_id} from project {project_id}")
                return {
                    "success": True,
                    "status": "success",
                    "message": f"Task '{task_details['title']}' deleted successfully",
                    "task_details": task_details
                }
            elif 'error' in verification:
                # Some other error occurred during verification
                logger.warning(f"Task deletion verification failed: {verification['error']}")
                return {
                    "status": "warning",
                    "message": f"Task deletion reported as successful, but verification failed: {verification['error']}",
                    "task_details": task_details,
                    "requires_verification": True
                }
            else:
                # Task still exists but deletion was processed by API
                logger.info(f"Task {task_id} still exists after deletion request - likely due to API sync delay")
                return {
                    "message": "Task deletion processed successfully. The task may still be accessible via direct API for some time due to TickTick's caching.",
                    "warning_code": "DELETION_SYNC_DELAY",
                    "status": "success",
                    "has_sync_delay": True,
                    "task_details": task_details
                }
            
        except Exception as e:
            logger.error(f"Unexpected error deleting task {task_id}: {e}")
            return {
                "error": f"Failed to delete task: {str(e)}",
                "error_code": "UNEXPECTED_ERROR",
                "status": "failed",
                "details": str(e)
            }