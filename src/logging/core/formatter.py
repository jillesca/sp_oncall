#!/usr/bin/env python3
"""
Custom formatters for sp_oncall logging.

This module provides OpenTelemetry-compatible structured logging formatters
and human-readable formatters for different output contexts.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional


class OTelFormatter(logging.Formatter):
    """
    OpenTelemetry-compatible JSON formatter.

    Produces structured JSON output compatible with observability tools
    and log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "filename": record.filename,
            "line_number": record.lineno,
        }

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": (
                    record.exc_info[0].__name__ if record.exc_info[0] else None
                ),
                "message": (
                    str(record.exc_info[1]) if record.exc_info[1] else None
                ),
                "traceback": (
                    self.formatException(record.exc_info)
                    if record.exc_info
                    else None
                ),
            }

        # Add extra fields from the log record
        extra_fields = self._extract_extra_fields(record)
        if extra_fields:
            log_entry["extra"] = extra_fields

        return json.dumps(log_entry, default=str)

    def _extract_extra_fields(
        self, record: logging.LogRecord
    ) -> Dict[str, Any]:
        """Extract extra fields from log record."""
        # Standard fields that should not be included in extra
        standard_fields = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "getMessage",
            "exc_info",
            "exc_text",
            "stack_info",
            "message",
            "asctime",
        }

        extra = {}
        for key, value in record.__dict__.items():
            if key not in standard_fields and not key.startswith("_"):
                extra[key] = value

        return extra


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter for console and file output.

    Provides clean, readable log output suitable for development
    and debugging scenarios.
    """

    def __init__(
        self, include_module: bool = True, include_extra: bool = True
    ):
        """
        Initialize the formatter.

        Args:
            include_module: Whether to include module name in output
            include_extra: Whether to include extra fields in output
        """
        self.include_module = include_module
        self.include_extra = include_extra

        # Define color codes for different log levels
        self.colors = {
            "DEBUG": "\033[36m",  # Cyan
            "INFO": "\033[32m",  # Green
            "WARNING": "\033[33m",  # Yellow
            "ERROR": "\033[31m",  # Red
            "CRITICAL": "\033[35m",  # Magenta
            "RESET": "\033[0m",  # Reset
        }

        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for human readability."""
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # Get color for level
        color = self.colors.get(record.levelname, "")
        reset = self.colors["RESET"]

        # Build base message
        parts = [
            f"{timestamp}",
            f"{color}{record.levelname:8}{reset}",
        ]

        # Add module name if requested
        if self.include_module:
            # Shorten logger name for readability
            logger_name = self._shorten_logger_name(record.name)
            parts.append(f"{logger_name:25}")

        # Add the actual message
        parts.append(record.getMessage())

        log_line = " | ".join(parts)

        # Add extra fields if present and requested
        if self.include_extra:
            extra_fields = self._extract_extra_fields(record)
            if extra_fields:
                extra_str = " | ".join(
                    f"{k}={v}" for k, v in extra_fields.items()
                )
                log_line += f" | {extra_str}"

        # Add exception information
        if record.exc_info:
            log_line += "\n" + self.formatException(record.exc_info)

        return log_line

    def _shorten_logger_name(self, name: str, max_length: int = 25) -> str:
        """Shorten logger name for better readability."""
        if len(name) <= max_length:
            return name

        # Split by dots and abbreviate middle parts
        parts = name.split(".")
        if len(parts) <= 2:
            return name[: max_length - 3] + "..."

        # Keep first and last part, abbreviate middle
        first = parts[0]
        last = parts[-1]
        middle = ".".join(p[0] for p in parts[1:-1])

        shortened = f"{first}.{middle}.{last}"
        if len(shortened) <= max_length:
            return shortened

        # If still too long, truncate
        return shortened[: max_length - 3] + "..."

    def _extract_extra_fields(
        self, record: logging.LogRecord
    ) -> Dict[str, Any]:
        """Extract extra fields from log record."""
        # Standard fields that should not be included in extra
        standard_fields = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "getMessage",
            "exc_info",
            "exc_text",
            "stack_info",
            "message",
            "asctime",
        }

        extra = {}
        for key, value in record.__dict__.items():
            if key not in standard_fields and not key.startswith("_"):
                # Truncate long values for readability
                if isinstance(value, str) and len(value) > 100:
                    value = value[:97] + "..."
                extra[key] = value

        return extra
