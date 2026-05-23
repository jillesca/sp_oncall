"""
Core functionality for the Network Executor Node.

This module is the entry point for the executor workflow. It retrieves all
pending investigations, runs a per-device sub-graph for each concurrently,
and merges the results back into the GraphState.
"""

import asyncio
from dataclasses import replace
from typing import List, Optional

from langgraph.config import get_store

from schemas import GraphState, Investigation, InvestigationStatus
from src.configuration import Configuration
from src.logging import get_logger, log_node_execution
from src.util.device_store import (
    get_device_profile,
    get_device_history,
    update_device_profile,
    format_profile_for_context,
    format_history_for_context,
)

from .device_subgraph import DeviceState, device_subgraph
from .logging import log_incoming_state
from .state import update_state_with_investigations, update_state_with_global_error

logger = get_logger(__name__)


@log_node_execution("Network Executor")
def llm_network_executor(state: GraphState) -> GraphState:
    """
    Execute network investigations for all pending devices concurrently.

    Each pending investigation is executed inside its own per-device sub-graph
    that handles the execute → assess → retry loop internally.

    Before running sub-graphs, stored device profiles are loaded and injected
    into each investigation's context for historical awareness.
    After sub-graphs complete, dynamic facts are saved back to the store.

    Args:
        state: The current GraphState from the workflow

    Returns:
        Updated GraphState with execution results for all investigations
    """
    log_incoming_state(state)

    try:
        pending_investigations = state.get_pending_investigations()

        if not pending_investigations:
            logger.info("🔍 No pending investigations to execute")
            return state

        config = Configuration.from_context()
        store = get_store()

        enriched_investigations = _enrich_investigations_with_stored_profiles(
            store, pending_investigations
        )

        logger.info(
            "🚀 Starting per-device sub-graphs for %s investigation(s) (max_retries=%s)",
            len(enriched_investigations),
            config.max_retries_per_device,
        )

        completed_investigations = asyncio.run(
            _run_device_subgraphs_concurrently(
                enriched_investigations,
                state.trigger_context,
                config.max_retries_per_device,
                state.event_type,
            )
        )

        _save_execution_dynamic_facts(store, completed_investigations, state.trigger_context)

        return update_state_with_investigations(state, completed_investigations)

    except Exception as e:
        logger.error("❌ Executor failed: %s", e)
        return update_state_with_global_error(state, e)


def _enrich_investigations_with_stored_profiles(
    store, investigations: List[Investigation]
) -> List[Investigation]:
    """Load stored device profiles and history, inject both into each investigation."""
    enriched = []
    for investigation in investigations:
        profile = get_device_profile(store, investigation.device_name)
        history = get_device_history(store, investigation.device_name, limit=3)
        enriched.append(_inject_device_context(investigation, profile, history))
    return enriched


def _inject_device_context(
    investigation: Investigation, profile: dict, history: list
) -> Investigation:
    """Append stored profile facts and investigation history to the device profile field."""
    sections = []

    formatted_profile = format_profile_for_context(profile)
    if formatted_profile:
        sections.append(formatted_profile)

    formatted_history = format_history_for_context(history)
    if formatted_history:
        sections.append(formatted_history)

    if not sections:
        return investigation

    enriched_profile = "\n\n".join([investigation.device_profile] + sections)
    logger.debug(
        "Injected stored profile and history context into investigation for %s",
        investigation.device_name,
    )
    return replace(investigation, device_profile=enriched_profile)


def _save_execution_dynamic_facts(
    store,
    investigations: List[Investigation],
    trigger_context: str,
) -> None:
    """Persist per-device execution findings as dynamic facts for future runs."""
    for investigation in investigations:
        update_device_profile(
            store,
            investigation.device_name,
            dynamic_facts={
                "last_alert": trigger_context[:500],
                "last_known_state": investigation.status.value,
            },
        )


async def _run_device_subgraphs_concurrently(
    investigations: List[Investigation],
    trigger_context: str,
    max_retries: int,
    event_type: Optional[str] = None,
) -> List[Investigation]:
    """
    Run each device's sub-graph concurrently and collect results.

    Args:
        investigations: Pending investigations to execute
        trigger_context: Original trigger content for prompt building
        max_retries: Maximum execution attempts per device before giving up
        event_type: Alert event type forwarded to per-device planning for skill routing

    Returns:
        List of investigations updated with execution results and assessments
    """
    tasks = [
        device_subgraph.ainvoke(
            DeviceState(
                investigation=investigation,
                trigger_context=trigger_context,
                max_retries=max_retries,
                event_type=event_type,
            )
        )
        for investigation in investigations
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    return [
        _extract_investigation_from_result(result, original)
        for result, original in zip(results, investigations)
    ]


def _extract_investigation_from_result(
    result, original_investigation: Investigation
) -> Investigation:
    """Extract the final investigation from a sub-graph result or handle failure."""
    if isinstance(result, Exception):
        logger.error(
            "❌ Sub-graph failed for %s: %s",
            original_investigation.device_name,
            result,
        )
        return replace(
            original_investigation,
            status=InvestigationStatus.FAILED,
            error_details=str(result),
        )

    final_state: DeviceState = result
    return final_state.investigation
