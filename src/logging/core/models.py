#!/usr/bin/env python3
"""
Data models for logging configuration.

This module defines data classes that encapsulate logging configuration
instead of using dictionaries, following OOP principles for better
type safety and data encapsulation.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from pathlib import Path

from .enums import LogLevel, SuppressionMode


@dataclass(frozen=True)
class EnvironmentConfiguration:
    """
    Configuration from environment variables.

    Encapsulates logging configuration read from environment variables,
    replacing dictionary-based data exchange with proper type-safe objects.
    """

    global_level: Optional[str] = None
    module_levels: Optional[Dict[str, str]] = None
    enable_structured: Optional[bool] = None
    log_file: Optional[str] = None
    external_suppression_mode: Optional[str] = None


@dataclass(frozen=True)
class ModuleLevelConfiguration:
    """
    Configuration for module-specific log levels.

    Encapsulates the mapping of module names to their specific log levels,
    replacing the plain dictionary approach with a proper data structure.
    """

    levels: Dict[str, LogLevel] = field(default_factory=dict)

    @classmethod
    def from_string_dict(
        cls, string_levels: Dict[str, str]
    ) -> "ModuleLevelConfiguration":
        """Create configuration from string dictionary with validation."""
        parsed_levels = {}
        for module, level_str in string_levels.items():
            try:
                parsed_levels[module] = LogLevel.from_string(level_str)
            except ValueError:
                # Skip invalid levels silently to maintain robustness
                continue
        return cls(levels=parsed_levels)

    def to_string_dict(self) -> Dict[str, str]:
        """Convert to dictionary with string level values."""
        return {
            module: level.to_string() for module, level in self.levels.items()
        }

    def get_level_for_module(self, module_name: str) -> Optional[LogLevel]:
        """Get log level for a specific module."""
        return self.levels.get(module_name)

    def merge_with(
        self, other: "ModuleLevelConfiguration"
    ) -> "ModuleLevelConfiguration":
        """Merge with another configuration, other takes precedence."""
        merged_levels = self.levels.copy()
        merged_levels.update(other.levels)
        return ModuleLevelConfiguration(levels=merged_levels)


@dataclass
class LoggingConfiguration:
    """
    Complete logging configuration data structure.

    Encapsulates all logging configuration parameters in a single,
    well-typed data structure that replaces scattered parameters
    and dictionary-based configuration.
    """

    # Core configuration
    global_level: LogLevel = LogLevel.INFO
    module_levels: ModuleLevelConfiguration = field(
        default_factory=ModuleLevelConfiguration
    )

    # Output configuration
    enable_structured: bool = False
    enable_file_output: bool = True
    log_file: Optional[Path] = None

    # External library suppression
    enable_external_suppression: bool = True
    external_suppression_mode: SuppressionMode = SuppressionMode.LANGGRAPH

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.log_file is not None:
            self.log_file = Path(self.log_file)

    @classmethod
    def from_environment_and_params(
        cls,
        env_config: EnvironmentConfiguration,
        global_level: Optional[str] = None,
        module_levels: Optional[Dict[str, str]] = None,
        enable_structured: bool = False,
        enable_file_output: bool = True,
        log_file: Optional[str] = None,
        enable_external_suppression: bool = True,
        external_suppression_mode: str = "langgraph",
    ) -> "LoggingConfiguration":
        """
        Create configuration from environment and explicit parameters.

        Explicit parameters take precedence over environment values.

        Args:
            env_config: Configuration read from environment variables
            global_level: Explicit global log level
            module_levels: Explicit module-specific levels
            enable_structured: Enable structured (JSON) logging
            enable_file_output: Enable file logging
            log_file: Custom log file path
            enable_external_suppression: Enable external library suppression
            external_suppression_mode: Suppression strategy to use

        Returns:
            Validated LoggingConfiguration instance

        Raises:
            ValueError: If any configuration value is invalid
        """
        # Environment variables take precedence over explicit params when params are None
        resolved_global_level = (
            env_config.global_level or global_level or "info"
        )
        resolved_enable_structured = (
            env_config.enable_structured
            if env_config.enable_structured is not None
            else (enable_structured or False)
        )
        resolved_log_file = env_config.log_file or log_file
        resolved_suppression_mode = (
            env_config.external_suppression_mode
            or external_suppression_mode
            or "langgraph"
        )

        # Merge module levels: explicit first, then environment (environment takes precedence)
        merged_module_levels = {}
        if module_levels:
            merged_module_levels.update(module_levels)
        env_module_levels = env_config.module_levels or {}
        merged_module_levels.update(
            env_module_levels
        )  # Environment overrides explicit

        # Parse and validate
        try:
            parsed_global_level = LogLevel.from_string(resolved_global_level)
            parsed_module_config = ModuleLevelConfiguration.from_string_dict(
                merged_module_levels
            )
            parsed_suppression_mode = SuppressionMode.from_string(
                resolved_suppression_mode
            )
        except ValueError as e:
            raise ValueError(f"Invalid logging configuration: {e}") from e

        return cls(
            global_level=parsed_global_level,
            module_levels=parsed_module_config,
            enable_structured=resolved_enable_structured,
            enable_file_output=enable_file_output,
            log_file=Path(resolved_log_file) if resolved_log_file else None,
            enable_external_suppression=enable_external_suppression,
            external_suppression_mode=parsed_suppression_mode,
        )

    def equals_for_caching(self, other: "LoggingConfiguration") -> bool:
        """Check equality for caching purposes."""
        if not isinstance(other, LoggingConfiguration):
            return False

        return (
            self.global_level == other.global_level
            and self.module_levels.levels == other.module_levels.levels
            and self.enable_structured == other.enable_structured
            and self.enable_file_output == other.enable_file_output
            and self.log_file == other.log_file
            and self.enable_external_suppression
            == other.enable_external_suppression
            and self.external_suppression_mode
            == other.external_suppression_mode
        )
