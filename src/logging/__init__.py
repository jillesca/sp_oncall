#!/usr/bin/env python3
"""
sp_oncall logging module.

This module provides comprehensive logging functionality with OpenTelemetry compatibility,
structured logging, and module-specific log level control optimized for LangGraph applications.

Modular architecture:
- Core components: enums, models, logger names, formatters
- Configuration: environment reading, file utils, main configurator
- Suppression: external library noise reduction with strategies
- Decorators: operation tracking
- Utils: dynamic logger creation and level management

Key Components:
- LoggingConfigurator: Centralized logging configuration
- OTelFormatter: OpenTelemetry-compatible structured logging
- LoggerNames: Standardized logger naming hierarchy
- ExternalLibrarySuppressor: External library noise suppression
- Operation tracking with decorators
- Dynamic log level management

Usage:
    from src.logging import LoggingConfigurator, get_logger

    LoggingConfigurator.configure(global_level="info")
    module_logger = get_logger(__name__)
"""

# Core components
from .core import (
    LogLevel,
    SuppressionMode,
    EnvironmentVariable,
    LoggingConfiguration,
    ModuleLevelConfiguration,
    EnvironmentConfiguration,
    LoggerNames,
    OTelFormatter,
    HumanReadableFormatter,
)

# Configuration components
from .configuration import (
    LoggingConfigurator,
    EnvironmentConfigReader,
    LogFilePathGenerator,
    configure_langchain,
    LangChainConfigurator,
)

# Suppression components
from .suppression import (
    ExternalLibrarySuppressor,
    setup_cli_suppression,
    setup_langgraph_suppression,
    setup_development_suppression,
)

# Decorators
from .decorators import log_operation, log_async_operation, log_node_execution

# Utilities
from .utils.dynamic import get_logger, set_module_level, get_module_levels
from .utils.convenience import configure_logging
from .utils.debug_capture import (
    DebugCapture,
    debug_capture_object,
    debug_capture_with_context,
    conditional_debug_capture,
    get_debug_capture,
)

__all__ = [
    # Core components
    "LogLevel",
    "SuppressionMode",
    "EnvironmentVariable",
    "LoggingConfiguration",
    "ModuleLevelConfiguration",
    "EnvironmentConfiguration",
    "LoggerNames",
    "OTelFormatter",
    "HumanReadableFormatter",
    # Configuration
    "LoggingConfigurator",
    "EnvironmentConfigReader",
    "LogFilePathGenerator",
    "configure_langchain",
    "LangChainConfigurator",
    # Main API functions
    "get_logger",
    "configure_logging",
    # Operation tracking
    "log_operation",
    "log_async_operation",
    "log_node_execution",
    # Dynamic level management
    "set_module_level",
    "get_module_levels",
    # External suppression
    "ExternalLibrarySuppressor",
    "setup_cli_suppression",
    "setup_langgraph_suppression",
    "setup_development_suppression",
    # Debug capture utilities
    "DebugCapture",
    "debug_capture_object",
    "debug_capture_with_context",
    "conditional_debug_capture",
    "get_debug_capture",
]
