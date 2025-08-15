"""File loading and parsing utilities for the project."""

from __future__ import annotations

import json
import os
from pathlib import Path
import asyncio
from typing import Any, Optional

# Add logging
from src.logging import get_logger

logger = get_logger(__name__)


def read_text_file(path: str, encoding: str = "utf-8") -> str:
    """Read and return the contents of a text file.

    Raises the same exception the underlying open/read would raise.
    """
    logger.debug("Reading text file: %s", path)

    try:
        with open(path, "r", encoding=encoding) as f:
            content = f.read()
        logger.debug(
            "Successfully read text file %s, length: %s characters",
            path,
            len(content),
        )
        return content
    except Exception as e:
        logger.error("Failed to read text file %s: %s", path, e)
        raise


def load_json_file(path: str, encoding: str = "utf-8") -> Any:
    """Load a JSON file and return the parsed object."""
    logger.debug("Loading JSON file: %s", path)

    try:
        with open(path, "r", encoding=encoding) as f:
            data = json.load(f)
        logger.debug("Successfully loaded JSON file %s", path)
        return data
    except Exception as e:
        logger.error("Failed to load JSON file %s: %s", path, e)
        raise


def _find_project_root(start: Path) -> Path:
    """Find the project root by walking up looking for common markers.

    Markers include: pyproject.toml, .git, langgraph.json, README.md
    """
    markers = {"pyproject.toml", ".git", "langgraph.json", "README.md"}
    cur = start
    while True:
        if any((cur / m).exists() for m in markers):
            return cur
        parent = cur.parent
        if parent == cur:
            # Filesystem root
            return start
        cur = parent


def resolve_path(filename: str, start_dir: Optional[str] = None) -> str:
    """Resolve a filename to an absolute path.

    If `filename` is absolute, return it. If it's a bare name like
    '.mcp_config.json', search upward from `start_dir` (or this file's
    location) to find it in the project root.
    """
    # Absolute path
    if os.path.isabs(filename):
        return filename

    # If a directory was provided, start there; otherwise derive project root
    if start_dir:
        base = start_dir
    else:
        here = Path(__file__).resolve().parent  # .../src/util
        base = str(_find_project_root(here))

    # Walk up until filesystem root looking for the filename in each directory
    cur = base
    while True:
        candidate = os.path.join(cur, filename)
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent

    # Fallback to joining with base even if not found
    return os.path.join(base, filename)


def load_project_json(filename: str, start_dir: Optional[str] = None) -> Any:
    """Resolve a JSON filename via resolve_path and load it."""
    path = resolve_path(filename, start_dir=start_dir)
    return load_json_file(path)


async def load_json_file_async(path: str, encoding: str = "utf-8") -> Any:
    """Async wrapper to load a JSON file without blocking the event loop."""
    return await asyncio.to_thread(load_json_file, path, encoding)


async def load_project_json_async(
    filename: str, start_dir: Optional[str] = None
) -> Any:
    """Async version of load_project_json using to_thread for file IO."""
    path = resolve_path(filename, start_dir=start_dir)
    return await load_json_file_async(path)
