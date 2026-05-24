"""
Core functionality for the Investigation Reporter Node.

This module contains the main entry point for the reporter workflow that generates
comprehensive investigation reports. It is also the single store-write node:
after generating the report it persists dynamic facts and investigation history
for every device so future runs benefit from the context.
"""

from langchain_core.messages import AIMessage
from langgraph.config import get_store

from schemas import GraphState
from src.logging import get_logger, log_node_execution
from src.util.device_store import (
    append_device_history,
    build_history_summary,
    update_device_profile,
)
from nodes.common import load_model

from .context import build_report_context
from .generation import generate_report

logger = get_logger(__name__)


@log_node_execution("Investigation Reporter")
def investigation_report_node(state: GraphState) -> GraphState:
    """
    Generate a comprehensive investigation report.

    Orchestrates the report generation workflow by:
    1. Building comprehensive context from all investigations and the RCA finding
    2. Generating the final report using the LLM
    3. Persisting dynamic facts and history to the store for all devices
    4. Adding the final report as an AIMessage to the conversation
    5. Resetting investigation state for the next user request

    Args:
        state: The current GraphState with all investigation results and root_cause

    Returns:
        Updated GraphState with final report in messages and cleared investigations
    """
    total_devices = len(state.primary_investigations) + len(
        state.context_investigations
    )
    logger.info(
        "📄 Generating investigation report for %d devices (%d primary, %d context)",
        total_devices,
        len(state.primary_investigations),
        len(state.context_investigations),
    )

    try:
        report_context = build_report_context(state)
        model = load_model()
        final_report = generate_report(model, report_context)

        _log_successful_report_generation(final_report)
        _persist_investigation_results(state)
        logger.info("🔄 Resetting working state for next user request")

        return GraphState(
            messages=state.messages + [AIMessage(content=final_report)],
            primary_investigations=[],
            context_investigations=[],
        )

    except Exception as e:
        logger.error("❌ Investigation report generation failed: %s", e)
        error_report = f"Error generating investigation report. Details: {e}"

        return GraphState(
            messages=state.messages + [AIMessage(content=error_report)],
            primary_investigations=[],
            context_investigations=[],
        )


def _persist_investigation_results(state: GraphState) -> None:
    """Persist all investigation data to the store.

    Writes dynamic facts (investigation outcome) and appends a history summary
    for every device — both primary and context. Static topology facts (role,
    neighbors) are stored so future runs benefit from cached context.
    This is the single store-write point for the entire graph run.
    """
    store = get_store()
    all_investigations = state.primary_investigations + state.context_investigations

    for investigation in all_investigations:
        update_device_profile(
            store,
            investigation.device_name,
            static_facts={
                "role": investigation.role,
                "neighbors": investigation.neighbors,
            },
            dynamic_facts={
                "last_alert": state.trigger_context[:500],
                "last_known_state": investigation.status.value,
            },
        )
        summary = build_history_summary(
            status=investigation.status.value,
            report=investigation.report,
        )
        append_device_history(store, investigation.device_name, summary)
        logger.debug(
            "💾 Persisted facts and history for device: %s",
            investigation.device_name,
        )


def _log_successful_report_generation(report: str) -> None:
    """Log successful report generation details."""
    logger.info(
        "✅ Investigation report generation complete, length: %s characters",
        len(report),
    )
