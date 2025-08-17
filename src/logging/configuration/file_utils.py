#!/usr/bin/env python3
"""
Log file path management utilities.

This module provides utilities for managing log file paths with
sequential numbering and automatic directory creation.
"""

import os
import re
from pathlib import Path
from typing import Optional


class LogFilePathGenerator:
    """
    Utility for generating sequential log file paths.

    Provides automatic numbering and directory management for log files,
    following the pattern: sp_oncall_001.log, sp_oncall_002.log, etc.
    """

    DEFAULT_LOG_DIR = "logs"
    DEFAULT_LOG_PREFIX = "sp_oncall"
    DEFAULT_LOG_EXTENSION = ".log"

    @classmethod
    def get_next_log_file_path(
        cls,
        log_dir: Optional[str] = None,
        prefix: Optional[str] = None,
        extension: Optional[str] = None,
    ) -> Path:
        """
        Generate the next sequential log file path.

        Args:
            log_dir: Directory for log files (defaults to DEFAULT_LOG_DIR)
            prefix: Log file prefix (defaults to DEFAULT_LOG_PREFIX)
            extension: Log file extension (defaults to DEFAULT_LOG_EXTENSION)

        Returns:
            Path to the next log file in sequence
        """
        log_dir = log_dir or cls.DEFAULT_LOG_DIR
        prefix = prefix or cls.DEFAULT_LOG_PREFIX
        extension = extension or cls.DEFAULT_LOG_EXTENSION

        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # Find the highest existing number
        highest_num = cls._find_highest_log_number(log_path, prefix, extension)
        next_num = highest_num + 1

        filename = f"{prefix}_{next_num:03d}{extension}"
        return log_path / filename

    @classmethod
    def get_latest_log_file(
        cls,
        log_dir: Optional[str] = None,
        prefix: Optional[str] = None,
        extension: Optional[str] = None,
    ) -> Optional[Path]:
        """
        Get the path to the most recent log file.

        Args:
            log_dir: Directory for log files
            prefix: Log file prefix
            extension: Log file extension

        Returns:
            Path to the latest log file, or None if no log files exist
        """
        log_dir = log_dir or cls.DEFAULT_LOG_DIR
        prefix = prefix or cls.DEFAULT_LOG_PREFIX
        extension = extension or cls.DEFAULT_LOG_EXTENSION

        log_path = Path(log_dir)
        if not log_path.exists():
            return None

        highest_num = cls._find_highest_log_number(log_path, prefix, extension)
        if highest_num == 0:
            return None

        filename = f"{prefix}_{highest_num:03d}{extension}"
        return log_path / filename

    @classmethod
    def _find_highest_log_number(
        cls, log_dir: Path, prefix: str, extension: str
    ) -> int:
        """Find the highest number in existing log files."""
        if not log_dir.exists():
            return 0

        pattern = re.compile(
            f"^{re.escape(prefix)}_(\\d+){re.escape(extension)}$"
        )
        highest = 0

        for file_path in log_dir.iterdir():
            if file_path.is_file():
                match = pattern.match(file_path.name)
                if match:
                    num = int(match.group(1))
                    highest = max(highest, num)

        return highest

    @classmethod
    def ensure_log_directory(cls, log_dir: Optional[str] = None) -> Path:
        """
        Ensure log directory exists.

        Args:
            log_dir: Directory path to create

        Returns:
            Path to the created directory
        """
        log_dir = log_dir or cls.DEFAULT_LOG_DIR
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        return log_path
