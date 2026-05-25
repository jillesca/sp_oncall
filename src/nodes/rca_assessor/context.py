"""
Context building for root cause analysis assessment.

Assembles all investigation reports into a structured prompt for the
rca_assessor_node to synthesize a definitive root cause determination.
"""

from schemas import GraphState
from nodes.markdown_builder import MarkdownBuilder
from src.logging import get_logger

logger = get_logger(__name__)


def build_rca_context(state: GraphState) -> str:
    """
    Build the full context for root cause analysis from all investigation reports.

    Args:
        state: Current workflow state with all completed investigations

    Returns:
        Markdown-formatted context string for the RCA LLM
    """
    logger.debug(
        "📋 Building RCA context: %s primary, %s context investigations",
        len(state.completed_primary_investigations),
        len(state.completed_context_investigations),
    )

    builder = MarkdownBuilder()
    builder.add_header("Root Cause Analysis Context")

    builder.add_section("Trigger Context")
    builder.add_text(state.trigger_context)

    _add_primary_reports(builder, state)
    _add_context_reports(builder, state)

    context_string = builder.build()
    logger.debug(
        "📤 RCA context prepared (%d characters)", len(context_string)
    )
    return context_string


def _add_primary_reports(builder: MarkdownBuilder, state: GraphState) -> None:
    """Add primary device investigation reports."""
    builder.add_section("Primary Device Investigation Reports")

    if not state.completed_primary_investigations:
        builder.add_text("No primary device investigations available.")
        return

    for inv in state.completed_primary_investigations:
        builder.add_subsection(f"{inv.device_name} (role: {inv.role})")
        builder.add_bold_text("Status:", inv.status.value)
        if inv.objective:
            builder.add_bold_text("Objective:", inv.objective)
        if inv.report:
            builder.add_text(inv.report)
        elif inv.error_details:
            builder.add_bold_text("Error:", inv.error_details)
        else:
            builder.add_text("No report available.")
        builder.add_empty_line()


def _add_context_reports(builder: MarkdownBuilder, state: GraphState) -> None:
    """Add neighbor health check reports."""
    builder.add_section("Neighbor Health Check Reports")

    if not state.completed_context_investigations:
        builder.add_text("No neighbor health checks were performed.")
        return

    for inv in state.completed_context_investigations:
        builder.add_subsection(f"{inv.device_name} (role: {inv.role})")
        builder.add_bold_text("Status:", inv.status.value)
        if inv.report:
            builder.add_text(inv.report)
        elif inv.error_details:
            builder.add_bold_text("Error:", inv.error_details)
        else:
            builder.add_text("No report available.")
        builder.add_empty_line()
