"""
Context building for executor investigations.

This module handles building investigation context in markdown format
for MCP agent execution.
"""

from typing import List

from schemas import Investigation
from nodes.markdown_builder import MarkdownBuilder
from src.logging import get_logger

logger = get_logger(__name__)


def build_investigation_context(
    investigation: Investigation, trigger_context: str
) -> str:
    """
    Build context string for a specific investigation in markdown format.

    Args:
        investigation: Investigation to build context for
        trigger_context: Original trigger content (user query, alert, or upstream agent)

    Returns:
        Formatted context string in markdown for the MCP agent
    """
    builder = MarkdownBuilder()
    _add_investigation_details(builder, investigation, trigger_context)
    return builder.build()


def build_primary_investigation_context(
    device_context: str,
    completed_context_investigations: List[Investigation],
) -> str:
    """
    Append completed context device reports to a primary device's context string.

    Called before launching primary sub-graphs so each primary executor agent
    has full situational awareness of neighbor health check findings.

    Args:
        device_context: Existing device_context string for the primary device
        completed_context_investigations: Context investigations with completed reports

    Returns:
        Enriched device_context string including neighbor findings
    """
    if not completed_context_investigations:
        return device_context

    lines = [device_context, "", "Neighbor Health Check Results:"]
    for inv in completed_context_investigations:
        lines.append(f"\n  Device: {inv.device_name} (role={inv.role})")
        lines.append(f"  {inv.report}")

    return "\n".join(lines)


def _add_investigation_details(
    builder: MarkdownBuilder,
    investigation: Investigation,
    trigger_context: str,
) -> None:
    """Add main investigation details to the context."""
    builder.add_header("Investigation Context")
    builder.add_bold_text("Trigger Context:", trigger_context)
    builder.add_bold_text("Device Name:", investigation.device_name)
    builder.add_bold_text("Role:", investigation.role)
    builder.add_bold_text(
        "Objective:", investigation.objective or "Not specified"
    )

    builder.add_section("Device Context")
    builder.add_code_block(investigation.device_context)

    builder.add_section("Working Plan Steps")
    builder.add_text(
        investigation.working_plan_steps or "No plan steps defined"
    )
