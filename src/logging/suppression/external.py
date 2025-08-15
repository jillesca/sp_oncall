#!/usr/bin/env python3
"""
External library suppression functionality.

This module provides core functionality for suppressing verbose logging
from external libraries that tend to pollute application logs.
"""

import logging
import os
from typing import Dict

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
    def setup_langsmith_quiet_mode(cls) -> None:
        """
        Configure LangSmith to operate quietly while preserving functionality.

        This keeps tracing and observability working but reduces console noise.
        """
        langsmith_quiet_vars = {
            # Reduce LangSmith client verbosity while keeping functionality
            "LANGSMITH_CLIENT_LOG_LEVEL": "WARNING",
            # Keep tracing enabled but reduce HTTP request logging
            "LANGSMITH_QUIET": "true",
        }
        cls.setup_environment_suppression(langsmith_quiet_vars)

    @classmethod
    def get_langgraph_suppression_config(cls) -> Dict[str, LogLevel]:
        """Get suppression configuration for LangGraph applications."""
        return {
            # LangGraph components - reduce noise (DEFAULT SUPPRESSION)
            "langgraph_runtime_inmem.queue": LogLevel.ERROR,
            "langgraph_runtime_inmem.ops": LogLevel.ERROR,
            "langgraph_runtime_inmem": LogLevel.ERROR,
            "langgraph_api.server": LogLevel.ERROR,
            "langgraph_api.graph": LogLevel.ERROR,
            "langgraph_api.auth.middleware": LogLevel.ERROR,
            "langgraph_api.metadata": LogLevel.ERROR,
            "langgraph_api": LogLevel.ERROR,
            "langgraph_runtime": LogLevel.ERROR,
            "langgraph": LogLevel.ERROR,
            # Uvicorn - web server noise (DEFAULT SUPPRESSION)
            "uvicorn.error": LogLevel.ERROR,
            "uvicorn.access": LogLevel.ERROR,
            "uvicorn": LogLevel.ERROR,
            # ASGI - web framework debug noise (DEFAULT SUPPRESSION)
            "asgi": LogLevel.ERROR,
            "starlette": LogLevel.ERROR,
            "starlette.middleware": LogLevel.ERROR,
            "starlette.middleware.base": LogLevel.ERROR,
            # File watching (DEFAULT SUPPRESSION)
            "watchfiles.main": LogLevel.ERROR,
            "watchfiles": LogLevel.ERROR,
            # HTTP libraries (DEFAULT SUPPRESSION)
            "httpx": LogLevel.ERROR,
            "httpcore": LogLevel.ERROR,
            "urllib3": LogLevel.ERROR,
            "requests": LogLevel.ERROR,
            # LangChain libraries (DEFAULT SUPPRESSION)
            "langchain": LogLevel.ERROR,
            "langchain_openai": LogLevel.ERROR,
            "langchain_core": LogLevel.ERROR,
            "langchain_community": LogLevel.ERROR,
            # LangSmith tracing (SELECTIVE SUPPRESSION - keep functionality, reduce noise)
            "langsmith.client": LogLevel.WARNING,  # Allow errors/warnings, suppress debug/info
            "langsmith": LogLevel.WARNING,
            # Character encoding libraries (DEFAULT SUPPRESSION)
            "charset_normalizer": LogLevel.ERROR,
            "chardet": LogLevel.ERROR,
            # Other common libraries (DEFAULT SUPPRESSION)
            "asyncio": LogLevel.ERROR,
            "concurrent.futures": LogLevel.ERROR,
            # Warning suppression (DEFAULT SUPPRESSION)
            "py.warnings": LogLevel.ERROR,
            "pydantic": LogLevel.ERROR,
            # OpenAI client (DEFAULT SUPPRESSION)
            "openai._base_client": LogLevel.ERROR,
            "openai": LogLevel.ERROR,
        }

    @classmethod
    def get_cli_suppression_config(cls) -> Dict[str, LogLevel]:
        """Get suppression configuration for CLI applications."""
        return {
            # Moderate suppression for CLI tools
            "httpx": LogLevel.ERROR,
            "urllib3": LogLevel.ERROR,
            "requests": LogLevel.ERROR,
            "asyncio": LogLevel.ERROR,
        }

    @classmethod
    def get_development_suppression_config(cls) -> Dict[str, LogLevel]:
        """Get minimal suppression configuration for development."""
        return {
            # Minimal suppression - keep most logging for debugging
            "urllib3": LogLevel.INFO,
            "requests": LogLevel.INFO,
        }
