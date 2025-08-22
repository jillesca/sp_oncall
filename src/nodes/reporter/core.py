"""
Core functionality for the Investigation Reporter Node.

This module contains the main entry point for the reporter workflow that generates
comprehensive investigation reports and manages workflow session state.
"""

from schemas import GraphState
from src.logging import get_logger, log_node_execution
from nodes.common import load_model

from .context import build_report_context
from .generation import generate_report
from .session import update_workflow_session

logger = get_logger(__name__)


@log_node_execution("Investigation Reporter")
def investigation_report_node(state: GraphState) -> GraphState:
    """
    Generate a comprehensive investigation report and reset workflow state.

    This function orchestrates the complete report generation workflow by:
    1. Building comprehensive context from all investigations
    2. Setting up the LLM model for report generation
    3. Generating the final report using the LLM
    4. Updating workflow session with learned patterns and findings
    5. Resetting GraphState to initial state while preserving WorkflowSession

    Args:
        state: The current GraphState with all investigation results

    Returns:
        Reset GraphState with updated WorkflowSession and final_report populated
    """
    logger.info(
        "📄 Generating comprehensive investigation report for %d devices",
        len(state.investigations),
    )

    try:
        report_context = build_report_context(state)
        model = load_model()
        final_report = generate_report(model, report_context)

        # Update workflow session with the generated final report
        updated_session = update_workflow_session(state, final_report)

        _log_successful_report_generation(final_report)
        return _build_reset_state_with_report(
            state, final_report, updated_session
        )

    except Exception as e:
        logger.error("❌ Investigation report generation failed: %s", e)
        error_report = f"Error generating investigation report. Details: {e}"
        # Update workflow session even in error case to preserve learning
        error_sessions = update_workflow_session(state, error_report)
        return _build_reset_state_with_report(
            state, error_report, error_sessions
        )


def _log_successful_report_generation(report: str) -> None:
    """Log successful report generation details."""
    logger.info(
        "✅ Investigation report generation complete, length: %s characters",
        len(report),
    )


def _build_reset_state_with_report(state, final_report, updated_sessions):
    """
    Build a reset GraphState with only the final report and updated WorkflowSessions.

    Args:
        state: Current GraphState (used only for user_query to create fresh state)
        final_report: Generated final report
        updated_sessions: Updated list of WorkflowSessions with new session appended

    Returns:
        Reset GraphState with final_report and workflow_session populated
    """
    logger.debug("🔄 Building reset state with final report")

    # Create a fresh GraphState with only essential information preserved
    reset_state = GraphState(
        user_query=state.user_query,  # Keep original query for reference
        final_report=final_report,
        workflow_session=updated_sessions,
    )

    logger.info(
        "✅ GraphState reset complete. Preserved: final_report (%d chars), %d workflow_sessions",
        len(final_report),
        len(updated_sessions),
    )

    return reset_state
