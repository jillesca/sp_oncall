"""
Logging utilities for the executor node.

This module handles logging operations for the executor workflow,
providing debug information about incoming state and execution progress.
"""

from schemas import GraphState
from src.logging import get_logger

logger = get_logger(__name__)


def log_incoming_state(state: GraphState) -> None:
    """Log incoming state information for debugging purposes."""
    logger.debug(
        "📥 Executor received state: user_query='%s', investigations=%s total, "
        "ready_investigations=%s, current_retries=%s",
        state.user_query,
        len(state.investigations),
        len(state.get_ready_investigations()),
        state.current_retries,
    )

    ready_investigations = state.get_ready_investigations()
    if ready_investigations:
        logger.debug("📋 Ready investigations:")
        for i, investigation in enumerate(ready_investigations, 1):
            logger.debug(
                "  Investigation %s: device=%s, status=%s, objective='%s'",
                i,
                investigation.device_name,
                investigation.status,
                investigation.objective or "Not specified",
            )

    if state.workflow_session and len(state.workflow_session) > 0:
        sessions_with_reports = sum(
            1 for session in state.workflow_session if session.previous_report
        )
        logger.debug(
            "📚 Workflow session context available: %d sessions, %d sessions with reports",
            len(state.workflow_session),
            sessions_with_reports,
        )

    if state.current_retries > 0:
        logger.warning(
            "🔄 Retry execution #%s for workflow",
            state.current_retries,
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
