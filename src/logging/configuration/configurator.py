#!/usr/bin/env python3
"""
Main logging configurator for sp_oncall.
"""

import logging
import sys
from typing import Dict, Optional

from ..core.models import LoggingConfiguration
from ..core.enums import SuppressionMode
from ..core.logger_names import LoggerNames
from ..core.formatter import OTelFormatter, HumanReadableFormatter
from .environment import EnvironmentConfigReader
from .file_utils import LogFilePathGenerator


class LoggingConfigurator:
    """Main configurator for the sp_oncall logging system."""

    _configured: bool = False
    _current_config: Optional[LoggingConfiguration] = None

    @classmethod
    def configure(
        cls,
        global_level: Optional[str] = None,
        module_levels: Optional[Dict[str, str]] = None,
        enable_structured: bool = False,
        enable_file_output: bool = True,
        log_file: Optional[str] = None,
        enable_external_suppression: bool = True,
        external_suppression_mode: str = "langgraph",
        debug_mode: bool = False,
    ) -> logging.Logger:
        """Configure the logging system with the specified parameters."""
        # Read environment configuration
        env_config = EnvironmentConfigReader.read_configuration()

        try:
            config = LoggingConfiguration.from_environment_and_params(
                env_config=env_config,
                global_level=global_level,
                module_levels=module_levels,
                enable_structured=enable_structured,
                enable_file_output=enable_file_output,
                log_file=log_file,
                enable_external_suppression=enable_external_suppression,
                external_suppression_mode=external_suppression_mode,
                debug_mode=debug_mode,
            )
        except ValueError as e:
            raise ValueError(f"Invalid logging configuration: {e}") from e

        # Check if reconfiguration is needed
        if (
            cls._configured
            and cls._current_config
            and config.equals_for_caching(cls._current_config)
        ):
            return logging.getLogger(LoggerNames.APP_ROOT)

        # Apply the configuration
        cls._apply_configuration(config)
        cls._current_config = config
        cls._configured = True

        # Get and log initial message
        app_logger = logging.getLogger(LoggerNames.APP_ROOT)
        return app_logger

    @classmethod
    def _apply_configuration(cls, config: LoggingConfiguration) -> None:
        """Apply the logging configuration to the Python logging system."""
        # Clear existing configuration
        logging.getLogger().handlers.clear()

        # Set root logger level to DEBUG to allow all messages through
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        # Choose formatter based on structured logging setting
        if config.enable_structured:
            formatter = OTelFormatter()
        else:
            formatter = HumanReadableFormatter()

        # Configure console handler
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(config.global_level.name)
        root_logger.addHandler(console_handler)

        # Configure file handler if enabled
        if config.enable_file_output:
            file_path = (
                config.log_file
                or LogFilePathGenerator.get_next_log_file_path()
            )

            # Ensure log directory exists
            LogFilePathGenerator.ensure_log_directory(str(file_path.parent))

            file_handler = logging.FileHandler(file_path)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(config.global_level.name)
            root_logger.addHandler(file_handler)

        # Apply module-specific levels
        cls._apply_module_levels(config)

        # Apply external library suppression
        if config.enable_external_suppression:
            cls._apply_external_suppression(config.external_suppression_mode)

    @classmethod
    def _apply_module_levels(cls, config: LoggingConfiguration) -> None:
        """Apply module-specific log levels."""
        for module, level in config.module_levels.levels.items():
            logger = logging.getLogger(module)
            logger.setLevel(level.name)

    @classmethod
    def _apply_external_suppression(cls, mode: SuppressionMode) -> None:
        """Apply external library log suppression."""
        # Import here to avoid circular imports
        from ..suppression.strategies import get_suppression_strategy

        strategy = get_suppression_strategy(mode)
        strategy.apply_suppression()

    @classmethod
    def reset_configuration(cls) -> None:
        """Reset the logging configuration state."""
        cls._configured = False
        cls._current_config = None
