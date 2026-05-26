"""
Assessment context building functionality.

The assessor only needs to know whether the investigation report addresses
the objective — it does not need raw tool call JSON or full device context.
Keeping the context minimal reduces noise and token cost.

The executor produces ONE combined report for all devices in the phase.
Device plans (objectives and steps) are shown alongside the report so the
assessor can verify each device's objective was addressed.
"""

from schemas.state import Investigation
from src.util.xml_helpers import xml_wrap
from src.logging import get_logger

logger = get_logger(__name__)


def build_phase_assessment_context(
    investigation: Investigation,
    trigger_context: str,
) -> str:
    """Build minimal assessment context for the phase investigation.

    Passes only what the assessor needs: trigger, per-device plans
    (which include objectives), and the final combined report.
    Raw tool call results are excluded — too noisy, assessor cannot act on them.

    Args:
        investigation: The phase investigation to assess.
        trigger_context: Original trigger content.

    Returns:
        Formatted context string for the LLM assessor.
    """
    logger.debug(
        "📋 Building phase assessment context for %s device(s)",
        len(investigation.device_contexts),
    )

    sections = [xml_wrap("TRIGGER_CONTEXT", trigger_context)]
    sections.append(_format_phase_assessment_block(investigation))

    context_string = "\n\n".join(sections)
    logger.debug(
        "📤 Phase assessment context prepared (%d characters)", len(context_string)
    )
    return context_string


def _format_phase_assessment_block(investigation: Investigation) -> str:
    """Format the combined phase assessment block for the assessor."""
    plan_lines = []
    for device_name, plan in investigation.device_plans.items():
        plan_lines.append(f"<DEVICE name=\"{device_name}\">")
        plan_lines.append(plan or "No plan available.")
        plan_lines.append("</DEVICE>")

    plan_section = "\n".join(plan_lines) if plan_lines else "No device plans available."

    report = investigation.report or "No report available."

    lines = [
        "<PHASE_ASSESSMENT>",
        "**Investigation Plans (one per device):**",
        plan_section,
        "",
        "**Combined Report (covers all devices above):**",
        report,
        "</PHASE_ASSESSMENT>",
    ]
    return "\n".join(lines)
