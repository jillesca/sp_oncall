"""
Core functionality for the Investigation Reporter Node.

This module contains the main entry point for the reporter workflow that generates
comprehensive investigation reports. It is also the single store-write node:
after generating the report it persists dynamic facts and investigation history
for every device so future runs benefit from the context.
"""

from typing import Optional

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
    primary_device_count = sum(
        len(inv.device_contexts) for inv in state.completed_primary_investigations
    )
    total_devices = primary_device_count + len(state.context_device_names)

    logger.info(
        "📄 Generating investigation report for %d devices (%d primary, %d context)",
        total_devices,
        primary_device_count,
        len(state.context_device_names),
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
    for every device — both primary and context. This is the single store-write
    point for the entire graph run.
    """
    store = get_store()

    for device_name, report in state.context_device_reports.items():
        _persist_device(
            store,
            device_name,
            state.trigger_context,
            status="completed",
            report=report,
        )

    for investigation in state.completed_primary_investigations:
        for device_name in investigation.device_contexts:
            _persist_device(
                store,
                device_name,
                state.trigger_context,
                status=investigation.status.value,
                report=investigation.report,
            )


def _persist_device(
    store,
    device_name: str,
    trigger_context: str,
    status: str,
    report: Optional[str],
) -> None:
    """Write dynamic facts and history for a single device to the store."""
    update_device_profile(
        store,
        device_name,
        dynamic_facts={
            "last_alert": trigger_context[:500],
            "last_known_state": status,
        },
    )
    summary = build_history_summary(status=status, report=report)
    append_device_history(store, device_name, summary)
    logger.debug("💾 Persisted facts and history for device: %s", device_name)


def _log_successful_report_generation(report: str) -> None:
    """Log successful report generation details."""
    logger.info(
        "✅ Investigation report generation complete, length: %s characters",
        len(report),
    )
