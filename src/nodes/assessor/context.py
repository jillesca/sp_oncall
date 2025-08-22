"""
Assessment context building functionality.

This module handles building comprehensive assessment context from
investigations and workflow state for LLM evaluation.
"""

from schemas.state import GraphState, Investigation
from nodes.markdown_builder import MarkdownBuilder
from nodes.common.session_context import add_session_context_to_builder
from src.logging import get_logger

logger = get_logger(__name__)


def build_assessment_context(state: GraphState) -> str:
    """
    Build comprehensive assessment context from all investigations in markdown format.

    Args:
        state: Current workflow state

    Returns:
        Markdown-formatted context string for the LLM
    """
    logger.debug(
        "📋 Building assessment context for %d investigations",
        len(state.investigations),
    )

    builder = MarkdownBuilder()
    builder.add_header("Network Investigation Assessment Context")

    _add_user_query_section(builder, state)
    _add_retry_information_section(builder, state)
    _add_investigations_section(builder, state)
    _add_session_context_section(builder, state)

    context_string = builder.build()
    logger.debug(
        "📤 Assessment context prepared (%d characters)", len(context_string)
    )
    return context_string


def _add_user_query_section(
    builder: MarkdownBuilder, state: GraphState
) -> None:
    """Add user query section to the context."""
    builder.add_section("User Query")
    builder.add_text(state.user_query)


def _add_retry_information_section(
    builder: MarkdownBuilder, state: GraphState
) -> None:
    """Add retry information section if applicable."""
    if state.current_retries > 0:
        builder.add_section("Retry Information")
        builder.add_bullet(
            f"Current attempt: {state.current_retries} of {state.max_retries}"
        )
        previous_feedback = (
            state.assessment.feedback_for_retry
            if state.assessment and state.assessment.feedback_for_retry
            else "No specific feedback provided"
        )
        builder.add_bullet(f"Previous feedback: {previous_feedback}")


def _add_investigations_section(
    builder: MarkdownBuilder, state: GraphState
) -> None:
    """Add device investigations section to the context."""
    builder.add_section("Device Investigations")

    if not state.investigations:
        builder.add_text("No device investigations found.")
    else:
        for i, investigation in enumerate(state.investigations, 1):
            _add_investigation_details(builder, investigation, i)


def _add_investigation_details(
    builder: MarkdownBuilder, investigation: Investigation, index: int
) -> None:
    """
    Add individual investigation context to the markdown builder.

    Args:
        builder: Markdown builder instance
        investigation: Investigation object to format
        index: Investigation number for display
    """
    builder.add_subsection(
        f"Investigation {index}: {investigation.device_name}"
    )

    builder.add_bold_text("Status:", investigation.status.value)
    builder.add_bold_text(
        "Device Profile:", investigation.device_profile or "Not available"
    )
    builder.add_bold_text("Role:", investigation.role or "Not specified")
    builder.add_bold_text(
        "Objective:", investigation.objective or "Not specified"
    )

    builder.add_bold_text("Working Plan Steps:")
    builder.add_code_block(
        investigation.working_plan_steps or "No plan steps defined"
    )

    _add_execution_results_to_builder(builder, investigation.execution_results)

    if investigation.report:
        builder.add_bold_text("Investigation Report:")
        builder.add_code_block(investigation.report)

    if investigation.error_details:
        builder.add_bold_text("Error Details:", investigation.error_details)

    builder.add_separator()


def _add_session_context_section(
    builder: MarkdownBuilder, state: GraphState
) -> None:
    """Add workflow session context section using common session context module."""
    add_session_context_to_builder(
        builder, state, section_title="Workflow Session Context"
    )


def _add_execution_results_to_builder(
    builder: MarkdownBuilder, execution_results
) -> None:
    """
    Add execution results to the markdown builder.

    Args:
        builder: Markdown builder instance
        execution_results: List of execution results
    """
    if execution_results:
        builder.add_bold_text(
            "Execution Results:",
            f"{len(execution_results)} tool calls executed",
        )
        for j, result in enumerate(execution_results, 1):
            builder.add_bold_text(f"Tool Call {j}:", result.function)
            builder.add_bullet(f"Parameters: {result.params}")
            builder.add_bullet(f"Error: {result.error or 'None'}")

            # Add the full result content as JSON if available
            if result.result:
                builder.add_bold_text("Result:")
                builder.add_code_block(str(result))
            else:
                builder.add_bullet("Result: Not available")

            builder.add_empty_line()
    else:
        builder.add_bold_text(
            "Execution Results:", "No execution results available"
        )
