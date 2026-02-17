"""File system, shell, and network operation tools for KOV agent."""

import logging
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

import requests


ToolResult = Dict[str, Any]

ALLOWED_SHELL_COMMANDS = {
    "cat",
    "echo",
    "find",
    "git",
    "head",
    "ls",
    "pwd",
    "python",
    "python3",
    "pytest",
    "rg",
    "tail",
    "wc",
}


def _ok(data: Any, **meta: Any) -> ToolResult:
    return {"ok": True, "data": data, "error": None, "meta": meta}


def _err(message: str, **meta: Any) -> ToolResult:
    return {"ok": False, "data": None, "error": message, "meta": meta}


def _workspace_root() -> Path:
    """Return the allowed workspace root for file operations."""
    configured_root = os.environ.get("KOV_WORKSPACE_ROOT")
    return Path(configured_root or os.getcwd()).resolve()


def _resolve_workspace_path(path: str) -> Path:
    """Resolve paths and prevent escaping the configured workspace root."""
    if not path:
        raise ValueError("No path provided")

    root = _workspace_root()
    target = Path(path)
    resolved = (root / target).resolve() if not target.is_absolute() else target.resolve()

    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path '{path}' is outside workspace root '{root}'") from exc

    return resolved


def _is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def read_file(path: str) -> ToolResult:
    """Read contents of a file within the workspace root."""
    try:
        resolved = _resolve_workspace_path(path)
        if not resolved.exists() or not resolved.is_file():
            return _err(f"File not found: {path}", path=str(resolved))

        content = resolved.read_text(encoding="utf-8")
        logging.info("Read file: %s", resolved)
        return _ok(content, path=str(resolved))
    except Exception as exc:
        error_msg = f"Error reading {path}: {exc}"
        logging.error(error_msg)
        return _err(error_msg, path=path)


def write_file(data: Dict[str, Any]) -> ToolResult:
    """Write content to a file. Expects {'path': str, 'content': str}."""
    try:
        path = data.get("path")
        content = data.get("content", "")
        resolved = _resolve_workspace_path(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(str(content), encoding="utf-8")
        logging.info("Wrote file: %s", resolved)
        return _ok(f"Successfully wrote to {resolved}", path=str(resolved))
    except Exception as exc:
        error_msg = f"Error writing file: {exc}"
        logging.error(error_msg)
        return _err(error_msg, path=data.get("path"))


def list_dir(path: str = ".") -> ToolResult:
    """List files in a directory within the workspace root."""
    try:
        resolved = _resolve_workspace_path(path)
        if not resolved.exists() or not resolved.is_dir():
            return _err(f"Directory not found: {path}", path=str(resolved))

        files = sorted(p.name for p in resolved.iterdir())
        logging.info("Listed directory: %s", resolved)
        return _ok(files, path=str(resolved))
    except Exception as exc:
        error_msg = f"Error listing directory {path}: {exc}"
        logging.error(error_msg)
        return _err(error_msg, path=path)


def delete_file(path: str) -> ToolResult:
    """Delete a file within the workspace root after confirmation."""
    try:
        resolved = _resolve_workspace_path(path)
        if not resolved.exists() or not resolved.is_file():
            return _err(f"File not found: {path}", path=str(resolved))

        confirm = input(f"Are you sure you want to delete '{resolved}'? (y/N): ")
        if confirm.lower() != "y":
            return _err("File deletion cancelled", path=str(resolved))

        resolved.unlink()
        logging.info("Deleted file: %s", resolved)
        return _ok(f"Successfully deleted {resolved}", path=str(resolved))
    except Exception as exc:
        error_msg = f"Error deleting {path}: {exc}"
        logging.error(error_msg)
        return _err(error_msg, path=path)


def run_shell(command: str) -> ToolResult:
    """Execute an allowlisted shell command without shell=True."""
    try:
        argv = shlex.split(command)
        if not argv:
            return _err("No command provided")

        if argv[0] not in ALLOWED_SHELL_COMMANDS:
            return _err(f"Command '{argv[0]}' is not in the allowlist", command=command)

        result = subprocess.run(argv, capture_output=True, text=True, cwd=str(_workspace_root()))
        output = (result.stdout or "") + (result.stderr or "")
        logging.info("Executed shell command: %s", command)
        return _ok(
            output.strip(),
            command=command,
            returncode=result.returncode,
            succeeded=result.returncode == 0,
        )
    except Exception as exc:
        error_msg = f"Error executing command '{command}': {exc}"
        logging.error(error_msg)
        return _err(error_msg, command=command)


def fetch_url(url: str) -> ToolResult:
    """Fetch content from a URL."""
    if not _is_safe_url(url):
        return _err("Invalid URL. Only http/https URLs are allowed.", url=url)

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        logging.info("Fetched URL: %s", url)
        text = response.text[:2000]
        return _ok(text, url=url, status_code=response.status_code)
    except requests.exceptions.RequestException as exc:
        error_msg = f"Error fetching {url}: {exc}"
        logging.error(error_msg)
        return _err(error_msg, url=url)
    except Exception as exc:
        error_msg = f"Unexpected error fetching {url}: {exc}"
        logging.error(error_msg)
        return _err(error_msg, url=url)


def download_file(url: str, filename: str) -> ToolResult:
    """Download a file from URL to a workspace-local filename."""
    if not _is_safe_url(url):
        return _err("Invalid URL. Only http/https URLs are allowed.", url=url)

    try:
        resolved = _resolve_workspace_path(filename)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        resolved.write_bytes(response.content)
        logging.info("Downloaded %s to %s", url, resolved)
        return _ok(
            f"Successfully downloaded {url} to {resolved}",
            url=url,
            path=str(resolved),
            bytes=len(response.content),
            status_code=response.status_code,
        )
    except requests.exceptions.RequestException as exc:
        error_msg = f"Error downloading {url}: {exc}"
        logging.error(error_msg)
        return _err(error_msg, url=url, filename=filename)
    except Exception as exc:
        error_msg = f"Unexpected error downloading {url}: {exc}"
        logging.error(error_msg)
        return _err(error_msg, url=url, filename=filename)
