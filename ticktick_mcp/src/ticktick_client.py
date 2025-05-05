import os
import json
import base64
import requests
import logging
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
    
    def _make_request(self, method: str, endpoint: str, data=None) -> Dict:
        """
        Makes a request to the TickTick API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            data: Request data (for POST, PUT)
        
        Returns:
            API response as a dictionary
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            # Log request details for debugging
            logger.debug(f"Making {method} request to {url}")
            if data:
                logger.debug(f"Request data: {json.dumps(data, indent=2)}")
            
            # Make the request
            if method == "GET":
                response = requests.get(url, headers=self.headers)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Check if the request was unauthorized (401)
            if response.status_code == 401:
                logger.info("Access token expired. Attempting to refresh...")
                
                # Try to refresh the access token
                if self._refresh_access_token():
                    logger.info("Token refreshed. Retrying request...")
                    # Retry the request with the new token
                    if method == "GET":
                        response = requests.get(url, headers=self.headers)
                    elif method == "POST":
                        response = requests.post(url, headers=self.headers, json=data)
                    elif method == "DELETE":
                        response = requests.delete(url, headers=self.headers)
                else:
                    logger.error("Failed to refresh token. Please re-authenticate.")
                    return {"error": "Authentication failed. Please run 'uv run -m ticktick_mcp.cli auth' to reauthenticate."}
            
            # Capture detailed error information from 4xx/5xx responses
            if response.status_code >= 400:
                error_message = f"API request failed with status code: {response.status_code}"
                try:
                    error_detail = response.json()
                    error_message += f" - {json.dumps(error_detail)}"
                except Exception:
                    error_message += f" - {response.text if response.text else 'No error details available'}"
                    
                logger.error(error_message)
                return {"error": error_message}
            
            # Return empty dict for 204 No Content
            if response.status_code == 204:
                return {"success": True, "message": "Operation completed successfully"}
            
            # Parse and validate the response
            try:
                result = response.json()
                logger.debug(f"API response: {json.dumps(result, indent=2)}")
                return result
            except json.JSONDecodeError:
                if response.text:
                    return {"error": f"Invalid JSON response: {response.text}"}
                return {"success": True, "message": "Operation completed successfully"}
                
        except requests.exceptions.RequestException as e:
            error_message = f"API request failed: {str(e)}"
            logger.error(error_message)
            return {"error": error_message}
    
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
                   priority: int = 0, is_all_day: bool = False, repeat_flag: str = None) -> Dict:
        """Creates a new task."""
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
                   repeat_flag: str = None) -> Dict:
        """Updates an existing task."""
        # First, get the current task to preserve existing data
        try:
            current_task = self.get_task(project_id, task_id)
            if 'error' in current_task:
                return current_task  # Return the error
            
            # Start with the current task data
            data = {
                "id": task_id,
                "projectId": project_id
            }
            
            # Update only the fields that are provided
            if title is not None:
                data["title"] = title
            elif "title" in current_task:
                data["title"] = current_task["title"]
                
            if content is not None:
                data["content"] = content
            elif "content" in current_task:
                data["content"] = current_task["content"]
                
            if priority is not None:
                data["priority"] = priority
            elif "priority" in current_task:
                data["priority"] = current_task["priority"]
                
            if start_date is not None:
                data["startDate"] = start_date
            elif "startDate" in current_task:
                data["startDate"] = current_task["startDate"]
                
            if due_date is not None:
                data["dueDate"] = due_date
            elif "dueDate" in current_task:
                data["dueDate"] = current_task["dueDate"]
                
            if repeat_flag is not None:
                data["repeatFlag"] = repeat_flag
            elif "repeatFlag" in current_task:
                data["repeatFlag"] = current_task["repeatFlag"]
            
            # Include status if present in the current task
            if "status" in current_task:
                data["status"] = current_task["status"]
                
            # Include isAllDay if present in the current task
            if "isAllDay" in current_task:
                data["isAllDay"] = current_task["isAllDay"]
            
            # Log the update data for debugging
            logger.debug(f"Updating task {task_id} with data: {json.dumps(data, indent=2)}")
            
            return self._make_request("POST", f"/task/{task_id}", data)
            
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}")
            return {"error": f"Failed to update task: {str(e)}"}
    
    def complete_task(self, project_id: str, task_id: str) -> Dict:
        """Marks a task as complete."""
        return self._make_request("POST", f"/project/{project_id}/task/{task_id}/complete")
    
    def delete_task(self, project_id: str, task_id: str) -> Dict:
        """Deletes a task."""
        try:
            # Verify task exists before attempting to delete
            task = self.get_task(project_id, task_id)
            if 'error' in task:
                return {"error": f"Cannot delete task: {task['error']}"}
            
            # Task exists, proceed with deletion
            logger.info(f"Deleting task {task_id} from project {project_id}")
            result = self._make_request("DELETE", f"/project/{project_id}/task/{task_id}")
            
            # Verify deletion was successful by checking if task still exists
            if 'error' not in result:
                verification = self.get_task(project_id, task_id)
                if 'error' in verification and "404" in str(verification['error']):
                    # Task not found after deletion, this is expected
                    return {"success": True, "message": f"Task {task_id} deleted successfully"}
                elif 'error' in verification:
                    # Some other error occurred during verification
                    logger.warning(f"Task deletion verification failed: {verification['error']}")
                    return {"success": True, "message": f"Task {task_id} deletion reported as successful, but verification failed"}
                else:
                    # Task still exists
                    logger.error(f"Task {task_id} still exists after deletion attempt")
                    return {"error": "Task deletion reported as successful, but task still exists"}
            
            return result
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            return {"error": f"Failed to delete task: {str(e)}"}