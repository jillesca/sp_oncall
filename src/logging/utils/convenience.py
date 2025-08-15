#!/usr/bin/env python3
"""
Convenience functions for the logging system.

This module provides simple, high-level functions for common logging
operations.
"""

from typing import Dict, Optional

from .dynamic import (
    get_logger as _get_logger,
    set_module_level,
    get_module_levels,
)
from ..configuration.configurator import LoggingConfigurator


def get_logger(name: str):
    """Get a logger for the specified module."""
    return _get_logger(name)


def configure_logging(
    level: str = "info",
    structured: bool = False,
    debug: bool = False,
    module_levels: Optional[Dict[str, str]] = None,
) -> None:
    """
    Simple logging configuration function.

    Args:
        level: Global log level
        structured: Enable structured JSON logging
        debug: Enable debug mode
        module_levels: Module-specific log levels
    """
    LoggingConfigurator.configure(
        global_level=level,
        enable_structured=structured,
        debug_mode=debug,
        module_levels=module_levels,
    )


__all__ = [
    "get_logger",
    "configure_logging",
    "set_module_level",
    "get_module_levels",
]
