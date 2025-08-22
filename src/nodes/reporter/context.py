"""Context building for report generation."""

from schemas import GraphState
from schemas.state import Investigation, InvestigationStatus
from nodes.markdown_builder import MarkdownBuilder
from nodes.common.session_context import add_session_context_to_builder
from src.logging import get_logger

logger = get_logger(__name__)


def build_report_context(state: GraphState) -> str:
    """
    Build comprehensive report context from all investigations in markdown format.

    Args:
        state: Current workflow state with investigations and assessment

    Returns:
        Markdown-formatted context string for the LLM
    """
    logger.debug(
        "📋 Building report context for %d investigations",
        len(state.investigations),
    )

    builder = MarkdownBuilder()
    builder.add_header("Network Investigation Report Context")

    _add_user_query_section(builder, state)
    _add_investigation_overview(builder, state)
    _add_investigation_details(builder, state)
    _add_assessment_results(builder, state)
    _add_historical_context(builder, state)

    context_string = builder.build()
    logger.debug(
        "📤 Report context prepared (%d characters)", len(context_string)
    )
    return context_string


def _add_user_query_section(
    builder: MarkdownBuilder, state: GraphState
) -> None:
    """Add user query section."""
    builder.add_section("Original User Query")
    builder.add_text(state.user_query)


def _add_investigation_overview(
    builder: MarkdownBuilder, state: GraphState
) -> None:
    """Add investigation overview section."""
    builder.add_section("Investigation Overview")
    total_investigations = len(state.investigations)
    completed_investigations = [
        inv
        for inv in state.investigations
        if inv.status == InvestigationStatus.COMPLETED
    ]
    success_rate = (
        len(completed_investigations) / total_investigations
        if total_investigations > 0
        else 0.0
    )

    builder.add_bullet(f"Total devices investigated: {total_investigations}")
    builder.add_bullet(
        f"Successfully completed: {len(completed_investigations)}"
    )
    builder.add_bullet(f"Success rate: {success_rate:.1%}")
    builder.add_bullet(
        f"Retry attempts: {state.current_retries}/{state.max_retries}"
    )


def _add_investigation_details(
    builder: MarkdownBuilder, state: GraphState
) -> None:
    """Add individual investigation details."""
    builder.add_section("Device Investigation Results")
    if not state.investigations:
        builder.add_text("No device investigations found.")
    else:
        for i, investigation in enumerate(state.investigations, 1):
            _add_single_investigation_details(builder, investigation, i)


def _add_single_investigation_details(
    builder: MarkdownBuilder, investigation: Investigation, index: int
) -> None:
    """Add details for a single investigation."""
    status_icon = {
        InvestigationStatus.COMPLETED: "✅",
        InvestigationStatus.FAILED: "❌",
        InvestigationStatus.IN_PROGRESS: "🔄",
        InvestigationStatus.PENDING: "⏳",
        InvestigationStatus.SKIPPED: "⏭️",
    }.get(investigation.status, "❓")

    builder.add_subsection(
        f"Investigation {index}: {investigation.device_name}"
    )
    builder.add_bullet(f"Status: {status_icon} {investigation.status.value}")
    builder.add_bullet(f"Device Profile: {investigation.device_profile}")
    builder.add_bullet(f"Role: {investigation.role}")
    builder.add_bullet(f"Priority: {investigation.priority}")

    if investigation.objective:
        builder.add_bullet(f"Objective: {investigation.objective}")

    if investigation.dependencies:
        builder.add_bullet(
            f"Dependencies: {', '.join(investigation.dependencies)}"
        )

    builder.add_bullet(
        f"Execution steps: {len(investigation.execution_results)}"
    )

    if investigation.error_details:
        builder.add_text(f"**Error Details:** {investigation.error_details}")

    if investigation.report:
        builder.add_text("**Investigation Report:**")
        builder.add_text(investigation.report)

    if investigation.working_plan_steps:
        builder.add_text("**Working Plan:**")
        builder.add_text(investigation.working_plan_steps)

    builder.add_empty_line()


def _add_assessment_results(
    builder: MarkdownBuilder, state: GraphState
) -> None:
    """Add assessment results section."""
    builder.add_section("Assessment Results")
    if state.assessment:
        builder.add_bullet(
            f"Objective achieved: {state.assessment.is_objective_achieved}"
        )
        builder.add_text(
            f"**Assessment Notes:** {state.assessment.notes_for_final_report}"
        )
        if state.assessment.feedback_for_retry:
            builder.add_text(
                f"**Feedback for retry:** {state.assessment.feedback_for_retry}"
            )
    else:
        builder.add_text("No assessment results available.")


def _add_historical_context(
    builder: MarkdownBuilder, state: GraphState
) -> None:
    """Add historical context from workflow sessions using common session context module."""
    add_session_context_to_builder(
        builder, state, section_title="Historical Context"
    )
