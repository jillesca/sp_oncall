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
    """Add workflow session context if available."""
    if not state.workflow_session or len(state.workflow_session) == 0:
        return

    builder.add_separator()
    builder.add_section("Previous Investigation Context")
    builder.add_bold_text(
        "Total Investigation Sessions:", str(len(state.workflow_session))
    )

    # Use the most recent session for context
    latest_session = state.workflow_session[-1]

    _add_session_report(builder, latest_session.previous_report)
    _add_session_patterns(builder, latest_session.learned_patterns)
    _add_session_relationships(builder, latest_session.device_relationships)
    _add_historical_context(builder, state.workflow_session)


def _add_session_report(
    builder: MarkdownBuilder, previous_report: str
) -> None:
    """Add previous session report context."""
    if previous_report:
        builder.add_subsection("Recent Investigation Report")
        # Truncate for context
        report_preview = (
            previous_report[:200] + "..."
            if len(previous_report) > 200
            else previous_report
        )
        builder.add_text(report_preview)


def _add_session_patterns(
    builder: MarkdownBuilder, learned_patterns: str
) -> None:
    """Add learned patterns from recent session."""
    if learned_patterns:
        builder.add_subsection("Learned Patterns from Recent Session")
        # Show preview of patterns (first 300 characters)
        patterns_preview = (
            learned_patterns[:300] + "..."
            if len(learned_patterns) > 300
            else learned_patterns
        )
        builder.add_text(patterns_preview)


def _add_session_relationships(
    builder: MarkdownBuilder, device_relationships: str
) -> None:
    """Add device relationships from recent session."""
    if device_relationships:
        builder.add_subsection("Device Relationships from Recent Session")
        # Show preview of relationships (first 300 characters)
        relationships_preview = (
            device_relationships[:300] + "..."
            if len(device_relationships) > 300
            else device_relationships
        )
        builder.add_text(relationships_preview)


def _add_historical_context(
    builder: MarkdownBuilder, workflow_sessions
) -> None:
    """Add historical context if multiple sessions exist."""
    if len(workflow_sessions) > 1:
        builder.add_subsection("Historical Context")
        builder.add_text(
            f"{len(workflow_sessions)-1} previous sessions available for correlation"
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
