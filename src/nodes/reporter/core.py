"""
Core functionality for the Investigation Reporter Node.

This module contains the main entry point for the reporter workflow that generates
comprehensive investigation reports.
"""

from langchain_core.messages import AIMessage

from schemas import GraphState
from src.logging import get_logger, log_node_execution
from nodes.common import load_model

from .context import build_report_context
from .generation import generate_report

logger = get_logger(__name__)


@log_node_execution("Investigation Reporter")
def investigation_report_node(state: GraphState) -> GraphState:
    """
    Generate a comprehensive investigation report.

    This function orchestrates the report generation workflow by:
    1. Building comprehensive context from all investigations
    2. Setting up the LLM model for report generation
    3. Generating the final report using the LLM
    4. Adding the final report as an AIMessage to the conversation
    5. Resetting investigation state for the next user request

    Args:
        state: The current GraphState with all investigation results

    Returns:
        Updated GraphState with final report in messages and cleared investigations
    """
    logger.info(
        "📄 Generating comprehensive investigation report for %d devices",
        len(state.investigations),
    )

    try:
        report_context = build_report_context(state)
        model = load_model()
        final_report = generate_report(model, report_context)

        _log_successful_report_generation(final_report)
        logger.info("🔄 Resetting working state for next user request")

        return GraphState(
            messages=state.messages + [AIMessage(content=final_report)],
            investigations=[],
        )

    except Exception as e:
        logger.error("❌ Investigation report generation failed: %s", e)
        error_report = f"Error generating investigation report. Details: {e}"

        return GraphState(
            messages=state.messages + [AIMessage(content=error_report)],
            investigations=[],
        )


def _log_successful_report_generation(report: str) -> None:
    """Log successful report generation details."""
    logger.info(
        "✅ Investigation report generation complete, length: %s characters",
        len(report),
    )
