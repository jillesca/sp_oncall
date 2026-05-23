"""
Core functionality for the Network Executor Node.

This module is the entry point for the executor workflow. It retrieves all
pending investigations, runs a per-device sub-graph for each concurrently,
and merges the results back into the GraphState.
"""

import asyncio
from typing import List

from schemas import GraphState, Investigation, InvestigationStatus
from src.logging import get_logger, log_node_execution

from .logging import log_incoming_state
from .state import update_state_with_investigations, update_state_with_global_error
from .device_subgraph import DeviceState, device_subgraph

logger = get_logger(__name__)


@log_node_execution("Network Executor")
def llm_network_executor(state: GraphState) -> GraphState:
    """
    Execute network investigations for all pending devices concurrently.

    Each pending investigation is executed inside its own per-device sub-graph
    that handles the execute → assess → retry loop internally.

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

        logger.info(
            "🚀 Starting per-device sub-graphs for %s investigation(s)",
            len(pending_investigations),
        )

        completed_investigations = asyncio.run(
            _run_device_subgraphs_concurrently(
                pending_investigations, state.trigger_context
            )
        )

        return update_state_with_investigations(state, completed_investigations)

    except Exception as e:
        logger.error("❌ Executor failed: %s", e)
        return update_state_with_global_error(state, e)


async def _run_device_subgraphs_concurrently(
    investigations: List[Investigation], trigger_context: str
) -> List[Investigation]:
    """
    Run each device's sub-graph concurrently and collect results.

    Args:
        investigations: Pending investigations to execute
        trigger_context: Original trigger content for prompt building

    Returns:
        List of investigations updated with execution results and assessments
    """
    tasks = [
        device_subgraph.ainvoke(
            DeviceState(
                investigation=investigation,
                trigger_context=trigger_context,
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
        from dataclasses import replace

        return replace(
            original_investigation,
            status=InvestigationStatus.FAILED,
            error_details=str(result),
        )

    final_state: DeviceState = result
    return final_state.investigation
