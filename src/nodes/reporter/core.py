"""
Core functionality for the Investigation Reporter Node.

This module contains the main entry point for the reporter workflow that generates
comprehensive investigation reports and manages historical context state.
"""

from schemas import GraphState
from src.logging import get_logger, log_node_execution
from nodes.common import load_model

from .context import build_report_context
from .generation import generate_report
from .session import update_historical_context

logger = get_logger(__name__)


@log_node_execution("Investigation Reporter")
def investigation_report_node(state: GraphState) -> GraphState:
    """
    Generate a comprehensive investigation report and reset workflow state.

    This function orchestrates the complete report generation workflow by:
    1. Building comprehensive context from all investigations
    2. Setting up the LLM model for report generation
    3. Generating the final report using the LLM
    4. Updating historical context with learned patterns and findings
    5. Resetting GraphState to initial state while preserving HistoricalContext

    Args:
        state: The current GraphState with all investigation results

    Returns:
        Reset GraphState with updated HistoricalContext and final_report populated
    """
    logger.info(
        "📄 Generating comprehensive investigation report for %d devices",
        len(state.investigations),
    )

    try:
        report_context = build_report_context(state)
        model = load_model()
        final_report = generate_report(model, report_context)

        # Update historical context with the generated final report
        updated_context = update_historical_context(state, final_report)

        _log_successful_report_generation(final_report)
        return _build_reset_state_with_report(
            state, final_report, updated_context
        )

    except Exception as e:
        logger.error("❌ Investigation report generation failed: %s", e)
        error_report = f"Error generating investigation report. Details: {e}"
        # Update historical context even in error case to preserve learning
        error_contexts = update_historical_context(state, error_report)
        return _build_reset_state_with_report(
            state, error_report, error_contexts
        )


def _log_successful_report_generation(report: str) -> None:
    """Log successful report generation details."""
    logger.info(
        "✅ Investigation report generation complete, length: %s characters",
        len(report),
    )


def _build_reset_state_with_report(state, final_report, updated_contexts):
    """
    Build a reset GraphState with only the final report and updated HistoricalContext.

    Args:
        state: Current GraphState (used only for user_query to create fresh state)
        final_report: Generated final report
        updated_contexts: Updated list of HistoricalContext with new entry appended

    Returns:
        Reset GraphState with final_report and historical_context populated
    """
    logger.debug("🔄 Building reset state with final report")

    # Create a fresh GraphState with only essential information preserved
    reset_state = GraphState(
        user_query=state.user_query,  # Keep original query for reference
        final_report=final_report,
        historical_context=updated_contexts,
    )

    logger.info(
        "✅ GraphState reset complete. Preserved: final_report (%d chars), %d historical_contexts",
        len(final_report),
        len(updated_contexts),
    )

    return reset_state
