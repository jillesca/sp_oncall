"""
Context building for root cause analysis assessment.

The RCA assessor synthesizes investigation reports into a root cause.
It only needs: the trigger, the final reports, and device capabilities.
Raw tool JSON, working plans, and device context are excluded — the executor
already distilled these into the report.

The context phase produces a single combined report (context_phase_report).
Neighbor health check findings are sourced from that field rather than
iterating completed_context_investigations, which would repeat the same
content multiple times.
"""

from typing import List

from schemas import GraphState
from schemas.state import Investigation
from schemas.device_capability_profile import format_capability_profile_for_context
from src.util.xml_helpers import xml_wrap
from src.logging import get_logger

logger = get_logger(__name__)


def build_rca_context(state: GraphState) -> str:
    """Build the full context for root cause analysis from all investigation reports.

    Args:
        state: Current workflow state with all completed investigations.

    Returns:
        Formatted context string for the RCA LLM.
    """
    logger.debug(
        "📋 Building RCA context: %s primary, %s context investigations",
        len(state.completed_primary_investigations),
        len(state.completed_context_investigations),
    )

    sections = [xml_wrap("TRIGGER_CONTEXT", state.trigger_context)]

    primary_content = _format_primary_reports(state.completed_primary_investigations)
    sections.append(xml_wrap("PRIMARY_INVESTIGATION_REPORTS", primary_content))

    if state.context_phase_report:
        context_content = _format_context_phase_section(
            state.context_phase_report,
            state.completed_context_investigations,
        )
        sections.append(xml_wrap("NEIGHBOR_HEALTH_CHECK_REPORTS", context_content))

    context_string = "\n\n".join(sections)
    logger.debug("📤 RCA context prepared (%d characters)", len(context_string))
    return context_string


def _format_primary_reports(investigations: List[Investigation]) -> str:
    """Format primary investigation final reports, one section per device."""
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


def _format_context_phase_section(
    phase_report: str,
    investigations: List[Investigation],
) -> str:
    """Format the combined context phase report with a device summary header."""
    device_list = ", ".join(
        f"{inv.device_name} (role: {inv.role})" for inv in investigations
    )
    return f"**Devices checked:** {device_list}\n\n{phase_report}"
