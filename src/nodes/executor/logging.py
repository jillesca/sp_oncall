"""
Logging utilities for the executor node.

This module handles logging operations for the executor workflow,
providing debug information about incoming state and execution progress.
"""

from schemas import GraphState
from schemas.state import InvestigationStatus
from src.logging import get_logger

logger = get_logger(__name__)


def log_incoming_state(state: GraphState) -> None:
    """Log incoming state information for debugging purposes."""
    pending_investigations = [
        inv
        for inv in state.investigations
        if inv.status == InvestigationStatus.PENDING
    ]

    logger.debug(
        "📥 Executor received state: user_query='%s', investigations=%s total, pending=%s",
        state.trigger_context,
        len(state.investigations),
        len(pending_investigations),
    )

    if pending_investigations:
        logger.debug("📋 Pending investigations:")
        for i, investigation in enumerate(pending_investigations, 1):
            logger.debug(
                "  Investigation %s: device=%s, status=%s, objective='%s'",
                i,
                investigation.device_name,
                investigation.status,
                investigation.objective or "Not specified",
            )


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
