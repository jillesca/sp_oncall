#!/usr/bin/env python3
"""
Environment configuration reader for sp_oncall logging.

This module handles reading and parsing logging configuration from
environment variables, providing type-safe configuration objects.
"""

import os
from typing import Dict, Optional

from ..core.enums import EnvironmentVariable, LogLevel
from ..core.models import EnvironmentConfiguration


class EnvironmentConfigReader:
    """
    Reader for environment-based logging configuration.

    Provides centralized access to environment variables with proper
    parsing and validation for logging configuration.
    """

    @classmethod
    def read_configuration(cls) -> EnvironmentConfiguration:
        """
        Read logging configuration from environment variables.

        Returns:
            EnvironmentConfiguration with parsed values from environment
        """
        return EnvironmentConfiguration(
            global_level=cls._read_global_level(),
            module_levels=cls._parse_module_levels(cls._read_module_levels()),
            enable_structured=cls._parse_structured_logging(
                cls._read_structured_logging()
            ),
            log_file=cls._read_log_file(),
            external_suppression_mode=cls._read_suppression_mode(),
            debug_mode=cls._parse_debug_mode(cls._read_debug_mode()),
        )

    @classmethod
    def _read_global_level(cls) -> Optional[str]:
        """Read global log level from environment."""
        return os.getenv(EnvironmentVariable.LOG_LEVEL.value)

    @classmethod
    def _read_module_levels(cls) -> Optional[str]:
        """Read module-specific log levels from environment."""
        return os.getenv(EnvironmentVariable.MODULE_LEVELS.value)

    @classmethod
    def _read_structured_logging(cls) -> Optional[str]:
        """Read structured logging flag from environment."""
        return os.getenv(EnvironmentVariable.STRUCTURED_LOGGING.value)

    @classmethod
    def _read_log_file(cls) -> Optional[str]:
        """Read log file path from environment."""
        return os.getenv(EnvironmentVariable.LOG_FILE.value)

    @classmethod
    def _read_suppression_mode(cls) -> Optional[str]:
        """Read external suppression mode from environment."""
        return os.getenv(EnvironmentVariable.EXTERNAL_SUPPRESSION_MODE.value)

    @classmethod
    def _read_debug_mode(cls) -> Optional[str]:
        """Read debug mode flag from environment."""
        return os.getenv(EnvironmentVariable.DEBUG_MODE.value)

    @classmethod
    def _parse_module_levels(
        cls, module_levels_str: Optional[str]
    ) -> Optional[Dict[str, str]]:
        """Parse module-specific log levels from settings."""
        if not module_levels_str:
            return None

        module_levels = {}
        try:
            for pair in module_levels_str.split(","):
                if "=" not in pair:
                    continue

                module, level = pair.strip().split("=", 1)
                module = module.strip()
                level = level.strip().lower()

                # Validate level
                try:
                    LogLevel.from_string(level)
                    module_levels[module] = level
                except ValueError:
                    # Invalid level for this module, skip it
                    continue

        except Exception:
            # Malformed module levels, return empty dict
            return {}

        return module_levels if module_levels else None

    @classmethod
    def _parse_structured_logging(
        cls, structured_value: Optional[str]
    ) -> Optional[bool]:
        """Parse structured logging flag from settings."""
        if structured_value is None:
            return None

        return structured_value.lower() in ("true", "1", "yes", "on")

    @classmethod
    def _parse_debug_mode(cls, debug_value: Optional[str]) -> Optional[bool]:
        """Parse debug mode flag from settings."""
        if debug_value is None:
            return None

        return debug_value.lower() in ("true", "1", "yes", "on")
