"""
Context building for executor investigations.

This module handles building investigation context in markdown format
for MCP agent execution.
"""

from schemas import GraphState, Investigation
from nodes.markdown_builder import MarkdownBuilder
from src.logging import get_logger

logger = get_logger(__name__)


def build_investigation_context(
    investigation: Investigation, state: GraphState
) -> str:
    """
    Build context string for a specific investigation in markdown format.

    Args:
        investigation: Investigation to build context for
        state: Current GraphState for workflow context

    Returns:
        Formatted context string in markdown for the MCP agent
    """
    builder = MarkdownBuilder()
    _add_investigation_details(builder, investigation, state)
    return builder.build()


def _add_investigation_details(
    builder: MarkdownBuilder, investigation: Investigation, state: GraphState
) -> None:
    """Add main investigation details to the context."""
    builder.add_header("Investigation Context")
    builder.add_bold_text("User Query:", state.current_user_request)
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
