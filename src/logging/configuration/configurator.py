#!/usr/bin/env python3
"""
Main logging configurator for sp_oncall.
"""

import logging
import sys
from typing import Dict, Optional

from ..core.models import LoggingConfiguration
from ..core.enums import SuppressionMode, LogLevel
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

        # Configure warning filters for pydantic and other noisy warnings
        import warnings

        warnings.filterwarnings(
            "ignore", category=UserWarning, module="pydantic.*"
        )
        warnings.filterwarnings(
            "ignore", message=".*Default value.*not JSON serializable.*"
        )
        warnings.filterwarnings(
            "ignore", message=".*PydanticJsonSchemaWarning.*"
        )

        # Choose formatter based on structured logging setting
        if config.enable_structured:
            formatter = OTelFormatter()
        else:
            formatter = HumanReadableFormatter()

        # Determine the minimum handler level needed to accommodate module-specific levels
        handler_level = cls._determine_handler_level(config)

        # Configure console handler
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(handler_level.name)
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
            file_handler.setLevel(handler_level.name)
            root_logger.addHandler(file_handler)

        # Apply module-specific levels
        cls._apply_module_levels(config)

        # Set the app root logger to the global level to ensure proper inheritance
        # for loggers without specific configuration
        app_root_logger = logging.getLogger(LoggerNames.APP_ROOT)
        app_root_logger.setLevel(config.global_level.name)

        # Apply external library suppression
        if config.enable_external_suppression:
            cls._apply_external_suppression(config.external_suppression_mode)

    @classmethod
    def _determine_handler_level(
        cls, config: LoggingConfiguration
    ) -> LogLevel:
        """
        Determine the minimum handler level needed to accommodate all configured loggers.

        If module-specific levels include levels lower than the global level,
        the handlers need to be set to the lowest level to allow those messages through.
        The individual loggers will still filter based on their specific levels.
        """
        levels_to_consider = [config.global_level]

        # Add all module-specific levels
        for level in config.module_levels.levels.values():
            levels_to_consider.append(level)

        # Return the lowest (most permissive) level
        # LogLevel enum values are ordered from most to least permissive
        return min(levels_to_consider, key=lambda x: x.value)

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
