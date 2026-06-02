"""
Context building for root cause analysis assessment.

The RCA assessor synthesizes investigation reports into a root cause.
It only needs: the trigger, the final reports, and device names for headers.
Raw tool JSON, working plans, and device context are excluded — the executor
already distilled these into the report.
"""

from schemas import GraphState
from src.util.xml_helpers import xml_wrap
from nodes.common.investigation_context import (
    format_primary_reports,
    format_context_phase_section,
)
from src.logging import get_logger

logger = get_logger(__name__)


def build_rca_context(state: GraphState) -> str:
    """Build the full context for root cause analysis from all investigation reports.

    Args:
        state: Current workflow state with all completed investigations.

    Returns:
        Formatted context string for the RCA LLM.
    """
    logger.debug(
        "📋 Building RCA context: %s primary investigation(s), %s context device(s)",
        len(state.completed_primary_investigations),
        len(state.context_device_names),
    )

    sections = [xml_wrap("TRIGGER_CONTEXT", state.trigger_context)]

    primary_content = format_primary_reports(state.completed_primary_investigations)
    sections.append(xml_wrap("PRIMARY_INVESTIGATION_REPORTS", primary_content))

    if state.context_phase_report:
        context_content = format_context_phase_section(
            state.context_phase_report,
            state.context_device_names,
        )
        sections.append(xml_wrap("NEIGHBOR_HEALTH_CHECK_REPORTS", context_content))

    context_string = "\n\n".join(sections)
    logger.debug("📤 RCA context prepared (%d characters)", len(context_string))
    return context_string
