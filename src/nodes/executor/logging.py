"""
Logging utilities for the executor nodes.

This module handles logging operations for the executor workflow,
providing debug information about execution progress.
"""

from src.logging import get_logger

logger = get_logger(__name__)


def log_processed_data(
    investigation_report: str,
    executed_tool_calls,
) -> None:
    """Log processed data for debugging purposes."""
    logger.debug("📊 Processed data:")
    logger.debug(
        "  Investigation report length: %s characters",
        len(investigation_report),
    )
    logger.debug("  Executed calls count: %s", len(executed_tool_calls))

    if executed_tool_calls:
        logger.debug("📞 Processed calls details:")
        for i, call in enumerate(executed_tool_calls, 1):
            logger.debug(
                "  Call %s: %s (error: %s)",
                i,
                call.function,
                call.error or "None",
            )
