"""
Context building for report generation.

The reporter receives: the trigger, the RCA root cause, and the final
investigation reports. Raw tool JSON, working plans, and device context
are excluded — the executor already distilled these into the report,
and the reporter's job is narrative synthesis, not re-analysis.
"""

from schemas import GraphState
from src.util.xml_helpers import xml_wrap
from nodes.common.investigation_context import (
    format_primary_reports,
    format_context_phase_section,
)
from src.logging import get_logger

logger = get_logger(__name__)


def build_report_context(state: GraphState) -> str:
    """Build report context from the root cause and all investigation reports.

    Args:
        state: Current workflow state with investigations and root cause.

    Returns:
        Formatted context string for the reporter LLM.
    """
    logger.debug(
        "📋 Building report context (%d primary investigation(s), %d context device(s))",
        len(state.completed_primary_investigations),
        len(state.context_device_names),
    )

    sections = [xml_wrap("TRIGGER_CONTEXT", state.trigger_context)]

    root_cause = state.root_cause or "Root cause analysis was not completed."
    sections.append(xml_wrap("ROOT_CAUSE_ANALYSIS", root_cause))

    primary_content = format_primary_reports(state.completed_primary_investigations)
    sections.append(xml_wrap("PRIMARY_INVESTIGATION_REPORTS", primary_content))

    if state.context_phase_report:
        context_content = format_context_phase_section(
            state.context_phase_report,
            state.context_device_names,
        )
        sections.append(xml_wrap("NEIGHBOR_HEALTH_CHECK_REPORTS", context_content))

    context_string = "\n\n".join(sections)
    logger.debug("📤 Report context prepared (%d characters)", len(context_string))
    return context_string
