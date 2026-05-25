"""Context building for report generation.

The reporter receives: the trigger, the RCA root cause, and the final
investigation reports (one per device). Raw tool JSON, working plans, and
device context are excluded — the executor already distilled these into
the report, and the reporter's job is narrative synthesis, not re-analysis.
"""

from schemas import GraphState
from schemas.device_capability_profile import format_capability_profile_for_context
from src.util.xml_helpers import xml_wrap
from src.logging import get_logger

logger = get_logger(__name__)


def build_report_context(state: GraphState) -> str:
    """Build report context from the root cause and all investigation reports.

    Args:
        state: Current workflow state with investigations and root cause.

    Returns:
        Formatted context string for the reporter LLM.
    """
    total = len(state.completed_primary_investigations) + len(
        state.completed_context_investigations
    )
    logger.debug(
        "📋 Building report context for %d investigations (%d primary, %d context)",
        total,
        len(state.completed_primary_investigations),
        len(state.completed_context_investigations),
    )

    sections = [xml_wrap("TRIGGER_CONTEXT", state.trigger_context)]

    root_cause = state.root_cause or "Root cause analysis was not completed."
    sections.append(xml_wrap("ROOT_CAUSE_ANALYSIS", root_cause))

    primary_content = _format_reports(state.completed_primary_investigations)
    sections.append(xml_wrap("PRIMARY_INVESTIGATION_REPORTS", primary_content))

    if state.completed_context_investigations:
        context_content = _format_reports(state.completed_context_investigations)
        sections.append(xml_wrap("NEIGHBOR_HEALTH_CHECK_REPORTS", context_content))

    context_string = "\n\n".join(sections)
    logger.debug(
        "📤 Report context prepared (%d characters)", len(context_string)
    )
    return context_string


def _format_reports(investigations) -> str:
    """Format investigation final reports, one per device."""
    parts = []
    for inv in investigations:
        capability_context = format_capability_profile_for_context(inv.capability_profile)

        lines = [f"### {inv.device_name} (role: {inv.role}, status: {inv.status.value})"]

        if capability_context:
            lines.append(capability_context)

        if inv.report:
            lines.append(inv.report)
        elif inv.error_details:
            lines.append(f"**Error:** {inv.error_details}")
        else:
            lines.append("No report available.")

        parts.append("\n".join(lines))

    return "\n\n---\n\n".join(parts)
