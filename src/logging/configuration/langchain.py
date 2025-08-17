#!/usr/bin/env python3
"""
LangChain configuration module for sp_oncall.

This module handles LangChain-specific configuration including debug mode
using the existing Pydantic settings infrastructure.
"""


# Import logging after all local imports to avoid conflicts
import logging

from .environment import EnvironmentConfigReader

# Use standard logging to avoid circular imports with our logging module
logger = logging.getLogger("sp_oncall.logging.configuration.langchain")  # type: ignore


class LangChainConfigurator:
    """
    Configurator for LangChain-specific settings.

    Manages LangChain debug mode using the existing Pydantic settings
    infrastructure, ensuring consistency with the application's configuration
    management approach.
    """

    _configured: bool = False

    @classmethod
    def configure(cls) -> None:
        """
        Configure LangChain settings using the existing settings infrastructure.

        This method is idempotent and can be called multiple times safely.
        It reads configuration from the unified settings system.
        """
        if cls._configured:
            logger.debug("LangChain configuration already applied")
            return

        env_config = EnvironmentConfigReader.read_configuration()
        debug_mode = env_config.langchain_debug

        if debug_mode is not None:
            cls._set_debug_mode(debug_mode)
        else:
            logger.debug(
                "SP_ONCALL_LANGCHAIN_DEBUG not set, using default LangChain debug settings"
            )

        cls._configured = True
        logger.info("LangChain configuration completed")

    @classmethod
    def _set_debug_mode(cls, enabled: bool) -> None:
        """
        Set LangChain debug mode.

        Args:
            enabled: Whether to enable debug mode
        """
        try:
            from langchain_core.globals import set_debug

            set_debug(value=enabled)

            status = "enabled" if enabled else "disabled"
            logger.info(f"LangChain debug mode {status}")

        except ImportError as e:
            logger.error(f"Failed to import LangChain debug utilities: {e}")
        except Exception as e:
            logger.error(f"Failed to set LangChain debug mode: {e}")


def configure_langchain() -> None:
    """
    Convenience function to configure LangChain settings.

    This is the main entry point for LangChain configuration that should
    be called during application initialization.
    """
    LangChainConfigurator.configure()
