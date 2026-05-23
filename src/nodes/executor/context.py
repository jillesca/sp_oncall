"""
Context building for executor investigations.

This module handles building investigation context in markdown format
for MCP agent execution.
"""

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

    builder.add_section("Device Profile")
    builder.add_code_block(investigation.device_profile)

    builder.add_section("Working Plan Steps")
    builder.add_text(
        investigation.working_plan_steps or "No plan steps defined"
    )
