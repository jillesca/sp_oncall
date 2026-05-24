"""Context building for report generation."""

from schemas import GraphState
from schemas.state import Investigation, InvestigationStatus
from nodes.markdown_builder import MarkdownBuilder
from src.logging import get_logger

logger = get_logger(__name__)


def build_report_context(state: GraphState) -> str:
    """
    Build comprehensive report context from all investigations in markdown format.

    The report is structured in two sections:
    - Primary Device Investigations: root-cause findings for the alert targets
    - Neighbor Health Checks: health verification findings for context devices

    The root_cause produced by the rca_assessor_node is included as the
    authoritative synthesis so the reporter can present it directly.

    Args:
        state: Current workflow state with investigations and root cause

    Returns:
        Markdown-formatted context string for the LLM
    """
    total = len(state.primary_investigations) + len(state.context_investigations)
    logger.debug(
        "📋 Building report context for %d investigations (%d primary, %d context)",
        total,
        len(state.primary_investigations),
        len(state.context_investigations),
    )

    builder = MarkdownBuilder()
    builder.add_header("Network Investigation Report Context")

    _add_trigger_section(builder, state)
    _add_root_cause_section(builder, state)
    _add_primary_investigation_details(builder, state)
    _add_context_investigation_details(builder, state)

    context_string = builder.build()
    logger.debug(
        "📤 Report context prepared (%d characters)", len(context_string)
    )
    return context_string


def _add_trigger_section(
    builder: MarkdownBuilder, state: GraphState
) -> None:
    """Add trigger context section."""
    builder.add_section("Trigger Context")
    builder.add_text(state.trigger_context)


def _add_root_cause_section(
    builder: MarkdownBuilder, state: GraphState
) -> None:
    """Add the root cause determination from the RCA assessor."""
    builder.add_section("Root Cause Analysis")
    if state.root_cause:
        builder.add_text(state.root_cause)
    else:
        builder.add_text("Root cause analysis was not completed.")


def _add_primary_investigation_details(
    builder: MarkdownBuilder, state: GraphState
) -> None:
    """Add primary device investigation results."""
    builder.add_section("Primary Device Investigations")
    if not state.primary_investigations:
        builder.add_text("No primary device investigations were performed.")
        return
    for i, investigation in enumerate(state.primary_investigations, 1):
        _add_single_investigation(builder, investigation, i)


def _add_context_investigation_details(
    builder: MarkdownBuilder, state: GraphState
) -> None:
    """Add neighbor health check results."""
    builder.add_section("Neighbor Health Checks")
    if not state.context_investigations:
        builder.add_text("No neighbor health checks were performed.")
        return
    for i, investigation in enumerate(state.context_investigations, 1):
        _add_single_investigation(builder, investigation, i)


def _add_single_investigation(
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
    builder.add_bullet(f"Role: {investigation.role}")

    if investigation.objective:
        builder.add_bullet(f"Objective: {investigation.objective}")

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
