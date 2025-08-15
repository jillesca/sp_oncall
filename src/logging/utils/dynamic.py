#!/usr/bin/env python3
"""
Dynamic logger management utilities.

This module provides utilities for creating loggers and managing
log levels at runtime.
"""

import logging
from typing import Dict, Optional

from ..core.logger_names import LoggerNames


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Ensures logger names follow the application's naming convention
    and provides a centralized point for logger creation.

    Args:
        name: Logger name (usually __name__ from calling module)

    Returns:
        Logger instance
    """
    # Convert module name to application logger name if needed
    if name.startswith("src."):
        # Convert src.nodes.planner to sp_oncall.nodes.planner
        app_name = name.replace("src", LoggerNames.APP_ROOT, 1)
    elif name == "__main__":
        app_name = LoggerNames.APP_ROOT
    elif not name.startswith(LoggerNames.APP_ROOT):
        # For any other module, prefix with app root
        app_name = f"{LoggerNames.APP_ROOT}.{name}"
    else:
        app_name = name

    return logging.getLogger(app_name)


def set_module_level(module_name: str, level: str) -> None:
    """
    Set log level for a specific module at runtime.

    Args:
        module_name: Name of the module/logger
        level: Log level (debug, info, warning, error, critical)
    """
    from ..core.enums import LogLevel

    try:
        log_level = LogLevel.from_string(level)
        logger = logging.getLogger(module_name)
        logger.setLevel(log_level.name)
    except ValueError as e:
        raise ValueError(f"Invalid log level '{level}': {e}") from e


def get_module_levels() -> Dict[str, str]:
    """
    Get current log levels for all application loggers.

    Returns:
        Dictionary mapping logger names to their current levels
    """
    levels = {}

    # Get all loggers and filter for application loggers
    logger_dict = logging.Logger.manager.loggerDict

    for name, logger in logger_dict.items():
        if isinstance(
            logger, logging.Logger
        ) and LoggerNames.is_valid_logger_name(name):
            # Only include loggers that have an explicit level set
            if logger.level != logging.NOTSET:
                levels[name] = logging.getLevelName(logger.level).lower()

    return levels


def reset_module_levels() -> None:
    """Reset all module-specific log levels to NOTSET."""
    logger_dict = logging.Logger.manager.loggerDict

    for name, logger in logger_dict.items():
        if isinstance(
            logger, logging.Logger
        ) and LoggerNames.is_valid_logger_name(name):
            logger.setLevel(logging.NOTSET)
