"""
Assessment context building functionality.

The assessor only needs to know whether the investigation report addresses
the objective — it does not need raw tool call JSON, full device context,
or the working plan steps.

Working plan steps are guidelines for the executor, not a checklist for the
assessor. Excluding them prevents the assessor from penalising the executor
for not following optional steps, which caused false negatives in practice.

The executor produces ONE combined report for all devices in the phase.
Device objectives are shown alongside the report so the assessor can verify
each device's objective was addressed.
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

    Passes only what the assessor needs: trigger, per-device objectives
    (working plan steps deliberately excluded), and the final combined report.
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
    """Format the combined phase assessment block for the assessor.

    Only the objective is included per device — working plan steps are
    stripped so the assessor judges the report against the goal, not
    against the suggested investigation steps.
    """
    objective_lines = []
    for device_name, plan in investigation.device_plans.items():
        objective_lines.append(f'<DEVICE name="{device_name}">')
        objective_lines.append(_extract_objective(plan))
        objective_lines.append("</DEVICE>")

    objective_section = (
        "\n".join(objective_lines) if objective_lines else "No device objectives available."
    )

    report = investigation.report or "No report available."

    lines = [
        "<PHASE_ASSESSMENT>",
        "**Device Objectives (one per device):**",
        objective_section,
        "",
        "**Combined Report (covers all devices above):**",
        report,
        "</PHASE_ASSESSMENT>",
    ]
    return "\n".join(lines)


def _extract_objective(plan: str) -> str:
    """Extract only the objective line from a formatted device plan.

    The plan format from _format_device_plan is:
        **Objective:** <text>

        <WORKING_PLAN>
        ...steps...
        </WORKING_PLAN>

    The working plan section is intentionally excluded so the assessor
    judges whether the objective was met, not whether each step was taken.
    """
    if not plan:
        return "No objective available."

    objective_marker = "**Objective:**"
    working_plan_marker = "<WORKING_PLAN>"

    start = plan.find(objective_marker)
    if start == -1:
        return plan.strip()

    end = plan.find(working_plan_marker)
    objective_text = plan[start:end].strip() if end != -1 else plan[start:].strip()
    return objective_text
