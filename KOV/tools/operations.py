"""
File system and shell operation tools for KOV agent.
"""

import os
import logging
import subprocess
import requests
from typing import Dict, Any


def read_file(path: str) -> str:
    """Read contents of a file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        logging.info(f"Read file: {path}")
        return f"File contents of {path}:\n{content}"
    except FileNotFoundError:
        error_msg = f"File not found: {path}"
        logging.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error reading {path}: {str(e)}"
        logging.error(error_msg)
        return error_msg


def write_file(data: Dict[str, Any]) -> str:
    """Write content to a file. Expects dict with 'path' and 'content' keys."""
    try:
        path = data.get('path')
        content = data.get('content', '')
        
        if not path:
            return "Error: No file path provided"
            
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        logging.info(f"Wrote file: {path}")
        return f"Successfully wrote to {path}"
    except Exception as e:
        error_msg = f"Error writing file: {str(e)}"
        logging.error(error_msg)
        return error_msg


def list_dir(path: str = ".") -> str:
    """List files in a directory."""
    try:
        files = os.listdir(path)
        files.sort()
        logging.info(f"Listed directory: {path}")
        return f"Files in {path}:\n" + "\n".join(files)
    except Exception as e:
        error_msg = f"Error listing directory {path}: {str(e)}"
        logging.error(error_msg)
        return error_msg


def delete_file(path: str) -> str:
    """Delete a file with confirmation."""
    try:
        if not os.path.exists(path):
            return f"File not found: {path}"
            
        confirm = input(f"Are you sure you want to delete '{path}'? (y/N): ")
        if confirm.lower() != 'y':
            return "File deletion cancelled"
            
        os.remove(path)
        logging.info(f"Deleted file: {path}")
        return f"Successfully deleted {path}"
    except Exception as e:
        error_msg = f"Error deleting {path}: {str(e)}"
        logging.error(error_msg)
        return error_msg


def run_shell(command: str) -> str:
    """Execute a shell command and return output."""
    try:
        dangerous_commands = ['rm -rf', 'kill -9', 'sudo rm', 'format', 'mkfs']
        if any(cmd in command.lower() for cmd in dangerous_commands):
            confirm = input(f"Execute potentially destructive command '{command}'? (y/N): ")
            if confirm.lower() != 'y':
                return "Command execution cancelled"
        
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        output = result.stdout + result.stderr
        logging.info(f"Executed shell command: {command}")
        return f"Command: {command}\nOutput:\n{output}"
    except Exception as e:
        error_msg = f"Error executing command '{command}': {str(e)}"
        logging.error(error_msg)
        return error_msg


def fetch_url(url: str) -> str:
    """Fetch content from a URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        logging.info(f"Fetched URL: {url}")
        return f"Content from {url}:\n{response.text[:2000]}{'...' if len(response.text) > 2000 else ''}"
    except requests.exceptions.RequestException as e:
        error_msg = f"Error fetching {url}: {str(e)}"
        logging.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error fetching {url}: {str(e)}"
        logging.error(error_msg)
        return error_msg


def download_file(url: str, filename: str) -> str:
    """Download a file from URL."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(filename, 'wb') as f:
            f.write(response.content)
        
        logging.info(f"Downloaded {url} to {filename}")
        return f"Successfully downloaded {url} to {filename}"
    except requests.exceptions.RequestException as e:
        error_msg = f"Error downloading {url}: {str(e)}"
        logging.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error downloading {url}: {str(e)}"
        logging.error(error_msg)
        return error_msg
