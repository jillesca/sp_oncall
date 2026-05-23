"""
Assessment context building functionality.

This module handles building assessment context for a single device investigation,
used by the per-device sub-graph in the executor.
"""

from schemas.state import Investigation
from nodes.markdown_builder import MarkdownBuilder
from src.logging import get_logger

logger = get_logger(__name__)


def build_assessment_context(
    investigation: Investigation, trigger_context: str
) -> str:
    """
    Build assessment context for a single device investigation in markdown format.

    Args:
        investigation: The device investigation to assess
        trigger_context: Original trigger content (user query, alert, or upstream agent)

    Returns:
        Markdown-formatted context string for the LLM assessor
    """
    logger.debug(
        "📋 Building assessment context for device: %s",
        investigation.device_name,
    )

    builder = MarkdownBuilder()
    builder.add_header("Device Investigation Assessment Context")

    _add_trigger_context_section(builder, trigger_context)
    _add_investigation_details(builder, investigation)

    context_string = builder.build()
    logger.debug(
        "📤 Assessment context prepared (%d characters)", len(context_string)
    )
    return context_string


def _add_trigger_context_section(
    builder: MarkdownBuilder, trigger_context: str
) -> None:
    """Add the trigger context section to the assessment."""
    builder.add_section("Trigger Context")
    builder.add_text(trigger_context)


def _add_investigation_details(
    builder: MarkdownBuilder, investigation: Investigation
) -> None:
    """Add investigation details to the assessment context."""
    builder.add_section(f"Investigation: {investigation.device_name}")

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


def _add_execution_results_to_builder(
    builder: MarkdownBuilder, execution_results
) -> None:
    """Add execution results to the markdown builder."""
    if execution_results:
        builder.add_bold_text(
            "Execution Results:",
            f"{len(execution_results)} tool calls executed",
        )
        for j, result in enumerate(execution_results, 1):
            builder.add_bold_text(f"Tool Call {j}:", result.function)
            builder.add_bullet(f"Parameters: {result.params}")
            builder.add_bullet(f"Error: {result.error or 'None'}")

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
