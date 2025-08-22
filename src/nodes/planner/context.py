"""Context building for planner investigations."""

from typing import List
from schemas.state import Investigation, GraphState
from nodes.markdown_builder import MarkdownBuilder
from nodes.common.session_context import add_session_context_to_builder
from src.logging import get_logger

logger = get_logger(__name__)


def extract_investigations_summary(investigations: List[Investigation]) -> str:
    """
    Extract relevant investigation data for LLM planning context in markdown format.

    Args:
        investigations: List of Investigation objects from the state

    Returns:
        Markdown-formatted string containing device names and profiles for each investigation
    """
    if not investigations:
        return (
            MarkdownBuilder()
            .add_section("Investigations")
            .add_text("No investigations defined.")
            .build()
        )

    builder = MarkdownBuilder().add_section("Devices")

    for i, investigation in enumerate(investigations, 1):
        # Device header with numbering
        builder.add_subsection(f"{i}. Device: `{investigation.device_name}`")

        # Device profile section
        builder.add_bold_text("Device Profile:")
        builder.add_bold_text("Role:", investigation.role)
        builder.add_code_block(investigation.device_profile)

    logger.debug(
        "📊 Extracted markdown summary for %s devices",
        len(investigations),
    )
    return builder.build()


def build_planning_context(state: GraphState) -> str:
    """
    Build comprehensive planning context including investigations and session context.

    Args:
        state: Current GraphState with investigations and workflow sessions

    Returns:
        Markdown-formatted string containing complete planning context
    """
    logger.debug(
        "📋 Building planning context for %d investigations",
        len(state.investigations),
    )

    builder = MarkdownBuilder()
    builder.add_header("Planning Context")

    # Add investigations summary
    investigations_content = extract_investigations_summary(
        state.investigations
    )
    builder.add_text(investigations_content)

    # Add session context for historical awareness
    add_session_context_to_builder(
        builder, state, section_title="Historical Context for Planning"
    )

    context_string = builder.build()
    logger.debug(
        "📤 Planning context prepared (%d characters)", len(context_string)
    )
    return context_string
