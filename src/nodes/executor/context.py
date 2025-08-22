"""
Context building for executor investigations.

This module handles building investigation context in markdown format
for MCP agent execution.
"""

from schemas import GraphState, Investigation
from nodes.markdown_builder import MarkdownBuilder
from nodes.common.session_context import add_session_context_to_builder
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
    _add_workflow_session_context(builder, state)
    _add_retry_context(builder, state)

    return builder.build()


def _add_investigation_details(
    builder: MarkdownBuilder, investigation: Investigation, state: GraphState
) -> None:
    """Add main investigation details to the context."""
    builder.add_header("Investigation Context")
    builder.add_bold_text("User Query:", state.user_query)
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


def _add_workflow_session_context(
    builder: MarkdownBuilder, state: GraphState
) -> None:
    """Add workflow session context using the common session context module."""
    add_session_context_to_builder(
        builder, state, section_title="Previous Investigation Context"
    )


def _add_retry_context(builder: MarkdownBuilder, state: GraphState) -> None:
    """Add retry context if this is a retry."""
    if state.current_retries > 0:
        builder.add_separator()
        builder.add_section("Retry Context")
        builder.add_bold_text(
            "Retry Number:", f"#{state.current_retries} of {state.max_retries}"
        )

        feedback = (
            state.assessment.feedback_for_retry
            if state.assessment and state.assessment.feedback_for_retry
            else "No specific feedback provided from assessor"
        )
        builder.add_subsection("Previous Execution Feedback")
        builder.add_text(feedback)
