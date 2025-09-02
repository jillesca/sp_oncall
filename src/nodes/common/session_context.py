"""
Common historical context handling for HistoricalContext objects.

This module provides centralized logic for converting HistoricalContext objects
to markdown format, following DRY principles and ensuring consistent
formatting across all nodes.
"""

from typing import List

from schemas.state import GraphState, HistoricalContext
from nodes.markdown_builder import MarkdownBuilder
from src.logging import get_logger

logger = get_logger(__name__)


def add_historical_context_to_builder(
    builder: MarkdownBuilder,
    state: GraphState,
    section_title: str = "Previous Historical Context",
) -> None:
    """
    Add HistoricalContext to a MarkdownBuilder instance.

    This function provides a consistent way to add historical context across all nodes.
    It handles empty context lists gracefully and provides informative context
    about previous investigations, learned patterns, and device relationships.

    Args:
        builder: MarkdownBuilder instance to add content to
        state: GraphState containing historical_context data
        section_title: Title for the section (allows customization per node)
    """
    historical_contexts = (
        state.historical_context
        if state.historical_context is not None
        else []
    )

    if not historical_contexts:
        logger.debug("No historical contexts available")
        builder.add_section(section_title)
        builder.add_text(
            "**No previous historical context available.** "
            "This is the first investigation session."
        )
        return

    logger.debug(
        "Adding historical context for %d previous sessions",
        len(historical_contexts),
    )

    builder.add_section(section_title)
    builder.add_text(
        "**Note:** The following information comes from previous investigation sessions "
        "and provides historical context to inform the current analysis."
    )
    builder.add_empty_line()

    builder.add_bold_text(
        "Total Previous Sessions:", str(len(historical_contexts))
    )

    # Show the most recent context in detail
    latest_context = historical_contexts[-1]
    builder.add_subsection(f"Latest Session: {latest_context.session_id}")

    _add_session_report_context(builder, latest_context.previous_report)
    _add_learned_patterns_context(builder, latest_context.learned_patterns)
    _add_device_relationships_context(
        builder, latest_context.device_relationships
    )

    # If there are multiple contexts, show historical summary
    if len(historical_contexts) > 1:
        _add_historical_contexts_summary(builder, historical_contexts[:-1])


def _add_session_report_context(
    builder: MarkdownBuilder, previous_report: str
) -> None:
    """Add previous report context to the builder."""
    if previous_report:
        builder.add_bold_text("Previous Investigation Report:", "Available")
        # Show a meaningful preview
        preview = _get_text_preview(previous_report, 300)
        builder.add_code_block(preview)
    else:
        builder.add_bold_text(
            "Previous Investigation Report:", "Not available"
        )


def _add_learned_patterns_context(
    builder: MarkdownBuilder, learned_patterns: str
) -> None:
    """Add learned patterns context to the builder."""
    if learned_patterns:
        builder.add_bold_text("Learned Patterns from Previous Sessions:")
        builder.add_text(learned_patterns)
        builder.add_empty_line()
    else:
        builder.add_bold_text(
            "Learned Patterns:", "No patterns identified in previous sessions"
        )


def _add_device_relationships_context(
    builder: MarkdownBuilder, device_relationships: str
) -> None:
    """Add device relationships context to the builder."""
    if device_relationships:
        builder.add_bold_text("Device Relationships from Previous Sessions:")
        builder.add_text(device_relationships)
        builder.add_empty_line()
    else:
        builder.add_bold_text(
            "Device Relationships:",
            "No relationships identified in previous sessions",
        )


def _add_historical_contexts_summary(
    builder: MarkdownBuilder, historical_contexts: List[HistoricalContext]
) -> None:
    """Add summary of historical contexts for broader context."""
    builder.add_subsection("Historical Sessions Summary")
    builder.add_text(
        f"**{len(historical_contexts)} previous sessions** provide additional context:"
    )

    # Show last 3 historical contexts for context
    recent_historical = historical_contexts[-3:]

    for context in recent_historical:
        session_summary = []

        if context.previous_report:
            session_summary.append(
                f"report ({len(context.previous_report)} chars)"
            )
        if context.learned_patterns:
            session_summary.append(
                f"patterns ({len(context.learned_patterns)} chars)"
            )
        if context.device_relationships:
            session_summary.append(
                f"relationships ({len(context.device_relationships)} chars)"
            )

        summary_text = (
            ", ".join(session_summary) if session_summary else "minimal data"
        )
        builder.add_bullet(f"Session {context.session_id}: {summary_text}")


def _get_text_preview(text: str, max_length: int) -> str:
    """Get a preview of text with ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def build_historical_context_string(
    state: GraphState, section_title: str = "Previous Historical Context"
) -> str:
    """
    Build a standalone historical context string in markdown format.

    This is useful when you only need historical context without other content.

    Args:
        state: GraphState containing historical_context data
        section_title: Title for the section

    Returns:
        Markdown-formatted string containing historical context
    """
    builder = MarkdownBuilder()
    add_historical_context_to_builder(builder, state, section_title)
    return builder.build()


def has_historical_context(state: GraphState) -> bool:
    """
    Check if the state has any historical context available.

    Args:
        state: GraphState to check

    Returns:
        True if historical context is available, False otherwise
    """
    return (
        state.historical_context is not None
        and len(state.historical_context) > 0
    )
