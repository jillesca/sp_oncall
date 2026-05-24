"""
Core functionality for the Network Executor Nodes.

Two dedicated nodes handle execution in sequence:
1. context_executor_node — runs neighbor health-check investigations concurrently
2. primary_executor_node — runs primary (alert target) investigations concurrently,
   each receiving the original trigger and completed context device reports

Both nodes use the same per-device sub-graph (plan → execute → assess → retry).
The difference is the executor prompt and investigation role passed to each sub-graph.
"""

import asyncio
from dataclasses import replace
from typing import List, Optional

from schemas import GraphState, Investigation, InvestigationStatus
from src.configuration import Configuration
from src.logging import get_logger, log_node_execution

from .context import build_primary_investigation_context
from .device_subgraph import DeviceState, device_subgraph
from .state import (
    update_context_investigations,
    update_primary_investigations,
    mark_all_failed,
)

logger = get_logger(__name__)


@log_node_execution("Context Executor")
def context_executor_node(state: GraphState) -> GraphState:
    """
    Execute neighbor health-check investigations concurrently.

    Runs each context investigation through the per-device sub-graph using
    the context_executor prompt. Results are stored in context_investigations
    and made available to the primary executor node.

    Args:
        state: The current GraphState from the workflow

    Returns:
        Updated GraphState with completed context_investigations
    """
    if not state.context_investigations:
        logger.info("🔍 No context investigations to execute — skipping")
        return state

    config = Configuration.from_context()

    logger.info(
        "🚀 Starting context device sub-graphs for %s investigation(s)",
        len(state.context_investigations),
    )

    try:
        completed = asyncio.run(
            _run_device_subgraphs_concurrently(
                investigations=state.context_investigations,
                trigger_context=state.trigger_context,
                investigation_role="context",
                executor_prompt="context_executor",
                max_retries=config.max_retries_per_device,
                event_type=state.event_type,
            )
        )
        return update_context_investigations(state, completed)

    except Exception as e:
        logger.error("❌ Context executor failed: %s", e)
        return replace(
            state,
            context_investigations=mark_all_failed(
                state.context_investigations, e
            ),
        )


@log_node_execution("Primary Executor")
def primary_executor_node(state: GraphState) -> GraphState:
    """
    Execute primary (alert target) investigations concurrently.

    Each primary investigation receives the original trigger context plus
    the completed context device reports so it has full situational awareness.

    Args:
        state: The current GraphState from the workflow

    Returns:
        Updated GraphState with completed primary_investigations
    """
    if not state.primary_investigations:
        logger.info("🔍 No primary investigations to execute — skipping")
        return state

    config = Configuration.from_context()

    logger.info(
        "🚀 Starting primary device sub-graphs for %s investigation(s)",
        len(state.primary_investigations),
    )

    try:
        enriched_investigations = _enrich_with_context_reports(
            state.primary_investigations, state
        )

        completed = asyncio.run(
            _run_device_subgraphs_concurrently(
                investigations=enriched_investigations,
                trigger_context=state.trigger_context,
                investigation_role="primary",
                executor_prompt="network_executor",
                max_retries=config.max_retries_per_device,
                event_type=state.event_type,
            )
        )
        return update_primary_investigations(state, completed)

    except Exception as e:
        logger.error("❌ Primary executor failed: %s", e)
        return replace(
            state,
            primary_investigations=mark_all_failed(
                state.primary_investigations, e
            ),
        )


def _enrich_with_context_reports(
    investigations: List[Investigation], state: GraphState
) -> List[Investigation]:
    """Append completed context device reports to each primary investigation's context.

    This gives each primary executor agent full situational awareness of what
    the neighbor health checks found before it begins its own investigation.
    """
    completed_context = [
        inv
        for inv in state.context_investigations
        if inv.report
    ]

    if not completed_context:
        return investigations

    return [
        replace(
            inv,
            device_context=build_primary_investigation_context(
                inv.device_context, completed_context
            ),
        )
        for inv in investigations
    ]


async def _run_device_subgraphs_concurrently(
    investigations: List[Investigation],
    trigger_context: str,
    investigation_role: str,
    executor_prompt: str,
    max_retries: int,
    event_type: Optional[str] = None,
) -> List[Investigation]:
    """
    Run each device's sub-graph concurrently and collect results.

    Args:
        investigations: Investigations to execute
        trigger_context: Original trigger content for prompt building
        investigation_role: "primary" or "context" — shapes planning objective
        executor_prompt: Prompt file name to use for execution
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
                investigation_role=investigation_role,
                executor_prompt=executor_prompt,
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
