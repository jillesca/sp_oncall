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
    level: Optional[str] = None,
    structured: Optional[bool] = None,
    debug: Optional[bool] = None,
    module_levels: Optional[Dict[str, str]] = None,
) -> None:
    """
    Simple logging configuration function.

    Environment variables take precedence over these parameters.
    Only pass parameters to override environment configuration.

    Args:
        level: Global log level (environment variable SP_ONCALL_LOG_LEVEL takes precedence)
        structured: Enable structured JSON logging (environment variable takes precedence)
        debug: Enable debug mode (environment variable takes precedence)
        module_levels: Module-specific log levels (environment variable takes precedence)
    """
    LoggingConfigurator.configure(
        global_level=level,
        enable_structured=structured or False,
        debug_mode=debug or False,
        module_levels=module_levels,
    )


__all__ = [
    "get_logger",
    "configure_logging",
    "set_module_level",
    "get_module_levels",
]
