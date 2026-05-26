"""
Assessment context building functionality.

The assessor only needs to know whether the investigation report addresses
the objective — it does not need raw tool call JSON or full device context.
Keeping the context minimal reduces noise and token cost.

For the context phase, the executor produces ONE combined report for all
neighbor devices.  In that case all Investigation objects share the same
report text, so we present it once inside a PHASE_REPORT block rather than
repeating it per device.
"""

from typing import List

from schemas.state import Investigation
from src.util.xml_helpers import xml_wrap
from src.logging import get_logger

logger = get_logger(__name__)


def build_phase_assessment_context(
    investigations: List[Investigation],
    trigger_context: str,
) -> str:
    """Build minimal assessment context for all devices in a phase.

    Passes only what the assessor needs: trigger, objective, and the final
    report. Raw tool call results are excluded — they are too noisy and the
    assessor cannot act on them.

    When all investigations share the same report (combined context phase
    output), the report is shown once in a PHASE_REPORT block to avoid
    redundant duplication.

    Args:
        investigations: All device investigations in the phase.
        trigger_context: Original trigger content.

    Returns:
        Formatted context string for the LLM assessor.
    """
    logger.debug(
        "📋 Building phase assessment context for %s device(s)",
        len(investigations),
    )

    sections = [xml_wrap("TRIGGER_CONTEXT", trigger_context)]

    if _is_combined_phase_report(investigations):
        sections.append(_format_combined_phase_assessment(investigations))
    else:
        for inv in investigations:
            sections.append(_format_investigation_summary(inv))

    context_string = "\n\n".join(sections)
    logger.debug(
        "📤 Phase assessment context prepared (%d characters)", len(context_string)
    )
    return context_string


def _is_combined_phase_report(investigations: List[Investigation]) -> bool:
    """True when all investigations share one combined report (context phase pattern)."""
    if len(investigations) <= 1:
        return False
    reports = [inv.report for inv in investigations if inv.report]
    return len(reports) == len(investigations) and len(set(reports)) == 1


def _format_combined_phase_assessment(investigations: List[Investigation]) -> str:
    """Format a combined phase report for the assessor — show the shared report once."""
    objectives = "\n".join(
        f"- **{inv.device_name}** ({inv.role}): {inv.objective or 'Not specified'}"
        for inv in investigations
    )
    report = investigations[0].report
    lines = [
        "<PHASE_REPORT>",
        "**Devices and Objectives:**",
        objectives,
        "",
        "**Combined Report:**",
        report,
        "</PHASE_REPORT>",
    ]
    return "\n".join(lines)


def _format_investigation_summary(investigation: Investigation) -> str:
    """Format only the essential investigation fields for the assessor."""
    lines = [
        f"<INVESTIGATION device=\"{investigation.device_name}\" role=\"{investigation.role}\">",
        f"**Objective:** {investigation.objective or 'Not specified'}",
        "",
    ]

    if investigation.report:
        lines.append("**Report:**")
        lines.append(investigation.report)
    elif investigation.error_details:
        lines.append(f"**Error:** {investigation.error_details}")
    else:
        lines.append("**Report:** No report available.")

    lines.append("</INVESTIGATION>")
    return "\n".join(lines)
