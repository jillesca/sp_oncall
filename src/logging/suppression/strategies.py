#!/usr/bin/env python3
"""
External library suppression strategies.

This module provides different suppression strategies for various runtime
contexts (CLI, LangGraph, development), following the Strategy pattern.
"""

from abc import ABC, abstractmethod
from typing import Optional

from ..core.enums import SuppressionMode
from ..core.models import ModuleLevelConfiguration
from .external import ExternalLibrarySuppressor


class SuppressionStrategy(ABC):
    """
    Abstract base class for suppression strategies.

    Defines the interface for different suppression approaches
    based on runtime context.
    """

    @abstractmethod
    def apply_suppression(
        self, module_config: Optional[ModuleLevelConfiguration] = None
    ) -> None:
        """Apply suppression strategy."""
        pass


class CLISuppressionStrategy(SuppressionStrategy):
    """Suppression strategy optimized for CLI applications."""

    def apply_suppression(
        self, module_config: Optional[ModuleLevelConfiguration] = None
    ) -> None:
        """Apply moderate suppression suitable for CLI tools."""
        suppression_config = (
            ExternalLibrarySuppressor.get_cli_suppression_config()
        )
        ExternalLibrarySuppressor.suppress_libraries(suppression_config)


class LangGraphSuppressionStrategy(SuppressionStrategy):
    """Suppression strategy optimized for LangGraph applications."""

    def apply_suppression(
        self, module_config: Optional[ModuleLevelConfiguration] = None
    ) -> None:
        """Apply aggressive suppression for LangGraph applications."""
        # Set environment variables for early suppression
        env_vars = {
            "LANGCHAIN_TRACING_V2": "true",
            "LANGCHAIN_CALLBACKS_MANAGER": "true",
        }
        ExternalLibrarySuppressor.setup_environment_suppression(env_vars)

        # Configure LangSmith for quiet operation while preserving functionality
        ExternalLibrarySuppressor.setup_langsmith_quiet_mode()

        # Apply library-level suppression
        suppression_config = (
            ExternalLibrarySuppressor.get_langgraph_suppression_config()
        )
        ExternalLibrarySuppressor.suppress_libraries(suppression_config)


class DevelopmentSuppressionStrategy(SuppressionStrategy):
    """Suppression strategy for development/debugging."""

    def apply_suppression(
        self, module_config: Optional[ModuleLevelConfiguration] = None
    ) -> None:
        """Apply minimal suppression to preserve debugging information."""
        suppression_config = (
            ExternalLibrarySuppressor.get_development_suppression_config()
        )
        ExternalLibrarySuppressor.suppress_libraries(suppression_config)


# Strategy registry
_STRATEGIES = {
    SuppressionMode.CLI: CLISuppressionStrategy(),
    SuppressionMode.LANGGRAPH: LangGraphSuppressionStrategy(),
    SuppressionMode.DEVELOPMENT: DevelopmentSuppressionStrategy(),
}


def get_suppression_strategy(mode: SuppressionMode) -> SuppressionStrategy:
    """Get suppression strategy for the specified mode."""
    return _STRATEGIES[mode]


# Convenience functions for backward compatibility
def setup_cli_suppression(
    module_config: Optional[ModuleLevelConfiguration] = None,
) -> None:
    """Setup suppression optimized for CLI usage."""
    if module_config is None:
        module_config = ModuleLevelConfiguration()

    strategy = get_suppression_strategy(SuppressionMode.CLI)
    strategy.apply_suppression(module_config)


def setup_langgraph_suppression(
    module_config: Optional[ModuleLevelConfiguration] = None,
) -> None:
    """Setup suppression optimized for LangGraph applications."""
    if module_config is None:
        module_config = ModuleLevelConfiguration()

    strategy = get_suppression_strategy(SuppressionMode.LANGGRAPH)
    strategy.apply_suppression(module_config)


def setup_development_suppression(
    module_config: Optional[ModuleLevelConfiguration] = None,
) -> None:
    """Setup suppression for development/debugging."""
    if module_config is None:
        module_config = ModuleLevelConfiguration()

    strategy = get_suppression_strategy(SuppressionMode.DEVELOPMENT)
    strategy.apply_suppression(module_config)
