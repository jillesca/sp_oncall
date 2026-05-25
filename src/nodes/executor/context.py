"""
Context building for executor investigations.

Builds markdown-formatted investigation context passed to the MCP executor agent.
"""

from typing import List

from schemas import Investigation
from nodes.markdown_builder import MarkdownBuilder
from src.logging import get_logger

logger = get_logger(__name__)


def build_phase_context(
    investigations: List[Investigation],
    trigger_context: str,
) -> str:
    """Build combined context for all devices in an investigation phase.

    Produces a single markdown document covering every device in the phase,
    so the executor agent has full situational awareness in one prompt.
    """
    builder = MarkdownBuilder()
    builder.add_header("Investigation Context")
    builder.add_bold_text("Trigger Context:", trigger_context)
    builder.add_bold_text(
        "Devices:",
        ", ".join(f"{inv.device_name} ({inv.role})" for inv in investigations),
    )

    for inv in investigations:
        builder.add_section(f"Device: {inv.device_name}")
        builder.add_bold_text("Role:", inv.role)
        builder.add_bold_text("Objective:", inv.objective or "Not specified")
        if inv.working_plan_steps:
            builder.add_bold_text("Working Plan Steps:")
            builder.add_code_block(inv.working_plan_steps)
        builder.add_bold_text("Device Context:")
        builder.add_code_block(inv.device_context)

    return builder.build()


def build_primary_investigation_context(
    device_context: str,
    completed_context_investigations: List[Investigation],
) -> str:
    """Append completed context device reports to a primary device's context string.

    Called before launching the primary phase so the primary executor has full
    situational awareness of neighbor health check findings.
    """
    if not completed_context_investigations:
        return device_context

    lines = [device_context, "", "Neighbor Health Check Results:"]
    for inv in completed_context_investigations:
        lines.append(f"\n  Device: {inv.device_name} (role={inv.role})")
        lines.append(f"  {inv.report}")

    return "\n".join(lines)
