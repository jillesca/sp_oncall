"""
Core functionality for the Investigation Reporter Node.

This module contains the main entry point for the reporter workflow that generates
comprehensive investigation reports and manages historical context state.
"""

from langchain_core.messages import AIMessage

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
    Generate a comprehensive investigation report and prepare for next user request.

    This function orchestrates the complete report generation workflow by:
    1. Building comprehensive context from all investigations
    2. Setting up the LLM model for report generation
    3. Generating the final report using the LLM
    4. Adding the final report as an AIMessage to the conversation
    5. Updating historical context with learned patterns and findings
    6. Resetting working state (investigations, retries, assessment) for next request

    Args:
        state: The current GraphState with all investigation results

    Returns:
        Updated GraphState with final report in messages, updated HistoricalContext,
        and reset working state ready for next user request
    """
    logger.info(
        "📄 Generating comprehensive investigation report for %d devices",
        len(state.investigations),
    )

    try:
        report_context = build_report_context(state)
        model = load_model()
        final_report = generate_report(model, report_context)

        # Add the final report as an AIMessage to the conversation
        report_message = AIMessage(content=final_report)

        # Update historical context with the generated final report
        updated_context = update_historical_context(state, final_report)

        _log_successful_report_generation(final_report)
        logger.info("🔄 Resetting working state for next user request")

        # Return updated state with final report in messages and reset working state
        return GraphState(
            messages=state.messages + [report_message],
            investigations=[],  # Reset for next user request
            historical_context=updated_context,
            max_retries=3,  # Reset to default
            current_retries=0,  # Reset to default
            assessment=None,  # Reset to default
        )

    except Exception as e:
        logger.error("❌ Investigation report generation failed: %s", e)
        error_report = f"Error generating investigation report. Details: {e}"

        # Add error report as AIMessage
        error_message = AIMessage(content=error_report)

        # Update historical context even in error case to preserve learning
        error_contexts = update_historical_context(state, error_report)

        return GraphState(
            messages=state.messages + [error_message],
            investigations=[],  # Reset for next user request
            historical_context=error_contexts,
            max_retries=3,  # Reset to default
            current_retries=0,  # Reset to default
            assessment=None,  # Reset to default
        )


def _log_successful_report_generation(report: str) -> None:
    """Log successful report generation details."""
    logger.info(
        "✅ Investigation report generation complete, length: %s characters",
        len(report),
    )
