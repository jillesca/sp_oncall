"""
Common session context handling for WorkflowSession objects.

This module provides centralized logic for converting WorkflowSession objects
to markdown format, following DRY principles and ensuring consistent
formatting across all nodes.
"""

from typing import List

from schemas.state import GraphState, WorkflowSession
from nodes.markdown_builder import MarkdownBuilder
from src.logging import get_logger

logger = get_logger(__name__)


def add_session_context_to_builder(
    builder: MarkdownBuilder,
    state: GraphState,
    section_title: str = "Previous Session Context",
) -> None:
    """
    Add WorkflowSession context to a MarkdownBuilder instance.

    This function provides a consistent way to add session context across all nodes.
    It handles empty session lists gracefully and provides informative context
    about previous investigations, learned patterns, and device relationships.

    Args:
        builder: MarkdownBuilder instance to add content to
        state: GraphState containing workflow_session data
        section_title: Title for the section (allows customization per node)
    """
    sessions = (
        state.workflow_session if state.workflow_session is not None else []
    )

    if not sessions:
        logger.debug("No workflow sessions available for context")
        builder.add_section(section_title)
        builder.add_text(
            "**No previous session context available.** "
            "This is the first investigation session."
        )
        return

    logger.debug("Adding session context for %d sessions", len(sessions))

    builder.add_section(section_title)
    builder.add_text(
        "**Note:** The following information comes from previous investigation sessions "
        "and provides historical context to inform the current analysis."
    )
    builder.add_empty_line()

    builder.add_bold_text("Total Previous Sessions:", str(len(sessions)))

    # Show the most recent session in detail
    latest_session = sessions[-1]
    builder.add_subsection(f"Latest Session: {latest_session.session_id}")

    _add_session_report_context(builder, latest_session.previous_report)
    _add_learned_patterns_context(builder, latest_session.learned_patterns)
    _add_device_relationships_context(
        builder, latest_session.device_relationships
    )

    # If there are multiple sessions, show historical summary
    if len(sessions) > 1:
        _add_historical_sessions_summary(builder, sessions[:-1])


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


def _add_historical_sessions_summary(
    builder: MarkdownBuilder, historical_sessions: List[WorkflowSession]
) -> None:
    """Add summary of historical sessions for broader context."""
    builder.add_subsection("Historical Sessions Summary")
    builder.add_text(
        f"**{len(historical_sessions)} previous sessions** provide additional context:"
    )

    # Show last 3 historical sessions for context
    recent_historical = historical_sessions[-3:]

    for session in recent_historical:
        session_summary = []

        if session.previous_report:
            session_summary.append(
                f"report ({len(session.previous_report)} chars)"
            )
        if session.learned_patterns:
            session_summary.append(
                f"patterns ({len(session.learned_patterns)} chars)"
            )
        if session.device_relationships:
            session_summary.append(
                f"relationships ({len(session.device_relationships)} chars)"
            )

        summary_text = (
            ", ".join(session_summary) if session_summary else "minimal data"
        )
        builder.add_bullet(f"Session {session.session_id}: {summary_text}")


def _get_text_preview(text: str, max_length: int) -> str:
    """Get a preview of text with ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def build_session_context_string(
    state: GraphState, section_title: str = "Previous Session Context"
) -> str:
    """
    Build a standalone session context string in markdown format.

    This is useful when you only need session context without other content.

    Args:
        state: GraphState containing workflow_session data
        section_title: Title for the section

    Returns:
        Markdown-formatted string containing session context
    """
    builder = MarkdownBuilder()
    add_session_context_to_builder(builder, state, section_title)
    return builder.build()


def has_session_context(state: GraphState) -> bool:
    """
    Check if the state has any workflow session context available.

    Args:
        state: GraphState to check

    Returns:
        True if session context is available, False otherwise
    """
    return (
        state.workflow_session is not None and len(state.workflow_session) > 0
    )
