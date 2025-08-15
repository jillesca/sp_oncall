#!/usr/bin/env python3
"""
External library suppression functionality.

This module provides core functionality for suppressing verbose logging
from external libraries that tend to pollute application logs.
"""

import logging
import os
from typing import Dict, Optional

from ..core.models import ModuleLevelConfiguration
from ..core.enums import LogLevel


class ExternalLibrarySuppressor:
    """
    Core suppression functionality for external libraries.

    Provides utilities to suppress verbose logging from external libraries
    and frameworks that tend to generate excessive log noise.
    """

    @classmethod
    def suppress_libraries(cls, library_levels: Dict[str, LogLevel]) -> None:
        """
        Apply log level suppression to specified libraries.

        Args:
            library_levels: Dictionary mapping library names to desired log levels
        """
        for library, level in library_levels.items():
            logger = logging.getLogger(library)
            logger.setLevel(level.name)

    @classmethod
    def setup_environment_suppression(cls, env_vars: Dict[str, str]) -> None:
        """
        Set environment variables for external library suppression.

        Args:
            env_vars: Dictionary of environment variables to set
        """
        for key, value in env_vars.items():
            os.environ[key] = value

    @classmethod
    def get_langgraph_suppression_config(cls) -> Dict[str, LogLevel]:
        """Get suppression configuration for LangGraph applications."""
        return {
            # LangGraph components - reduce noise
            "langgraph_runtime_inmem.queue": LogLevel.ERROR,
            "langgraph_api.server": LogLevel.ERROR,
            "langgraph_api.graph": LogLevel.WARNING,
            "langgraph_api.auth.middleware": LogLevel.ERROR,
            "langgraph_api.metadata": LogLevel.ERROR,
            "langgraph": LogLevel.WARNING,
            # Uvicorn - web server noise
            "uvicorn.error": LogLevel.WARNING,
            "uvicorn.access": LogLevel.ERROR,
            "uvicorn": LogLevel.WARNING,
            # File watching
            "watchfiles.main": LogLevel.ERROR,
            "watchfiles": LogLevel.ERROR,
            # HTTP libraries
            "httpx": LogLevel.WARNING,
            "urllib3": LogLevel.WARNING,
            "requests": LogLevel.WARNING,
            # Other common libraries
            "asyncio": LogLevel.WARNING,
            "concurrent.futures": LogLevel.WARNING,
        }

    @classmethod
    def get_cli_suppression_config(cls) -> Dict[str, LogLevel]:
        """Get suppression configuration for CLI applications."""
        return {
            # Moderate suppression for CLI tools
            "httpx": LogLevel.WARNING,
            "urllib3": LogLevel.WARNING,
            "requests": LogLevel.WARNING,
            "asyncio": LogLevel.WARNING,
        }

    @classmethod
    def get_development_suppression_config(cls) -> Dict[str, LogLevel]:
        """Get minimal suppression configuration for development."""
        return {
            # Minimal suppression - keep most logging for debugging
            "urllib3": LogLevel.INFO,
            "requests": LogLevel.INFO,
        }
