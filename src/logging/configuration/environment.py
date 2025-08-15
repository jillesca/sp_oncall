#!/usr/bin/env python3
"""
Environment configuration reader for sp_oncall logging.

This module handles reading and parsing logging configuration from
environment variables using pydantic-settings for automatic .env file loading
and type-safe configuration objects.
"""

from typing import Dict, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggingSettings(BaseSettings):
    """
    Pydantic-based logging configuration from environment variables.

    Automatically loads from .env files and provides type-safe configuration
    with proper validation and default values.
    """

    model_config = SettingsConfigDict(
        # Load from .env file automatically
        env_file=".env",
        env_file_encoding="utf-8",
        # Environment variables take precedence over .env file
        env_prefix="SP_ONCALL_",
        # Case insensitive environment variable names
        case_sensitive=False,
        # Don't validate assignment (for better performance)
        validate_assignment=False,
        # Allow extra fields to ignore other environment variables
        extra="ignore",
    )

    # Core logging configuration
    log_level: Optional[str] = Field(
        default=None,
        description="Global log level (debug, info, warning, error, critical)",
    )

    module_levels: Optional[str] = Field(
        default=None,
        description="Module-specific log levels as comma-separated key=value pairs",
    )

    structured_logging: Optional[bool] = Field(
        default=None, description="Enable structured JSON logging"
    )

    log_file: Optional[str] = Field(
        default=None, description="Custom log file path"
    )

    external_suppression_mode: Optional[str] = Field(
        default=None,
        description="External library suppression strategy (cli, langgraph, development)",
    )

    debug_mode: Optional[bool] = Field(
        default=None, description="Enable debug mode for enhanced logging"
    )

    def get_parsed_module_levels(self) -> Optional[Dict[str, str]]:
        """Parse module levels string into dictionary."""
        if not self.module_levels:
            return None

        parsed = {}
        pairs = self.module_levels.split(",")
        for pair in pairs:
            if "=" in pair:
                module, level = pair.split("=", 1)
                parsed[module.strip()] = level.strip()
        return parsed


class EnvironmentConfigReader:
    """
    Reader for environment-based logging configuration.

    Provides centralized access to environment variables with proper
    parsing and validation for logging configuration using pydantic-settings.
    """

    _settings: Optional[LoggingSettings] = None

    @classmethod
    def get_settings(cls) -> LoggingSettings:
        """Get or create the logging settings instance."""
        if cls._settings is None:
            cls._settings = LoggingSettings()
        return cls._settings

    @classmethod
    def read_configuration(cls) -> "EnvironmentConfiguration":
        """
        Read logging configuration from environment variables.

        Returns:
            EnvironmentConfiguration with parsed values from environment
        """
        settings = cls.get_settings()

        # Import here to avoid circular imports
        from ..core.models import EnvironmentConfiguration

        return EnvironmentConfiguration(
            global_level=settings.log_level,
            module_levels=settings.get_parsed_module_levels(),
            enable_structured=settings.structured_logging,
            log_file=settings.log_file,
            external_suppression_mode=settings.external_suppression_mode,
            debug_mode=settings.debug_mode,
        )
