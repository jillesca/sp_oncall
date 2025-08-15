#!/usr/bin/env python3
"""
Core enums for sp_oncall logging system.

This module defines type-safe enums for log levels, suppression modes,
and environment variables, promoting consistent configuration throughout
the application.
"""

from enum import Enum


class LogLevel(Enum):
    """
    Standard logging levels with type safety.

    Provides conversion utilities and validation for log level strings
    used throughout the application.
    """

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @classmethod
    def from_string(cls, level_str: str) -> "LogLevel":
        """Convert string to LogLevel enum with validation."""
        normalized = level_str.lower().strip()
        for level in cls:
            if level.value == normalized:
                return level
        raise ValueError(
            f"Invalid log level: {level_str}. Valid levels: {[l.value for l in cls]}"
        )

    def to_string(self) -> str:
        """Convert LogLevel to string representation."""
        return self.value

    def __str__(self) -> str:
        return self.value


class SuppressionMode(Enum):
    """
    External library suppression modes.

    Each mode defines a different strategy for suppressing external
    library logging based on the runtime context.
    """

    CLI = "cli"  # Moderate suppression for CLI tools
    LANGGRAPH = (
        "langgraph"  # Aggressive suppression for LangGraph applications
    )
    DEVELOPMENT = "development"  # Minimal suppression for debugging

    @classmethod
    def from_string(cls, mode_str: str) -> "SuppressionMode":
        """Convert string to SuppressionMode enum with validation."""
        normalized = mode_str.lower().strip()
        for mode in cls:
            if mode.value == normalized:
                return mode
        raise ValueError(
            f"Invalid suppression mode: {mode_str}. Valid modes: {[m.value for m in cls]}"
        )

    def to_string(self) -> str:
        """Convert SuppressionMode to string representation."""
        return self.value

    def __str__(self) -> str:
        return self.value


class EnvironmentVariable(Enum):
    """
    Standard environment variable names for the application.

    Centralizes all environment variable names to prevent typos
    and ensure consistency across the application.
    """

    # Global logging settings
    LOG_LEVEL = "SP_ONCALL_LOG_LEVEL"
    STRUCTURED_LOGGING = "SP_ONCALL_STRUCTURED_LOGGING"
    LOG_FILE = "SP_ONCALL_LOG_FILE"

    # Module-specific settings
    MODULE_LEVELS = "SP_ONCALL_MODULE_LEVELS"

    # External library suppression
    EXTERNAL_SUPPRESSION_MODE = "SP_ONCALL_EXTERNAL_SUPPRESSION_MODE"

    # Debug settings
    DEBUG_MODE = "SP_ONCALL_DEBUG_MODE"

    def __str__(self) -> str:
        return self.value
