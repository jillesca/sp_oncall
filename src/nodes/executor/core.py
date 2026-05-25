"""
Dispatch functions for the device sub-graph phases.

Replaces the former executor nodes. Each phase has two pieces:
1. A dispatch function (conditional edge) — fans out via Send to device sub-graphs.
2. For the primary phase: a dispatch node that first enriches investigations
   with context reports before the conditional edge fans out.

Context phase runs first (Send → context_device_subgraph × N).
Primary phase runs second (Send → primary_device_subgraph × M), after all
context sub-graphs have written their results to completed_context_investigations.
"""

from dataclasses import replace
from typing import List, Union

from langgraph.types import Send

from schemas import GraphState, Investigation
from src.configuration import Configuration
from src.logging import get_logger, log_node_execution

from .context import build_primary_investigation_context
from .device_subgraph import DeviceState

logger = get_logger(__name__)


def dispatch_context_investigations(
    state: GraphState,
) -> Union[List[Send], str]:
    """Fan out one Send per context investigation, or skip to primary dispatch.

    Used as a conditional edge from input_validator_node. Returns a Send per
    context device so LangGraph runs them all concurrently as separate
    context_device_subgraph instances.
    """
    if not state.context_investigations:
        logger.info("🔍 No context investigations — skipping to primary dispatch")
        return "primary_dispatch_node"

    config = Configuration.from_context()
    logger.info(
        "🚀 Dispatching %s context device sub-graph(s)",
        len(state.context_investigations),
    )
    return [
        Send(
            "context_device_subgraph",
            DeviceState(
                investigation=inv,
                trigger_context=state.trigger_context,
                investigation_role="context",
                executor_prompt="context_executor",
                max_retries=config.max_retries_per_device,
                event_type=state.event_type,
            ),
        )
        for inv in state.context_investigations
    ]


@log_node_execution("Primary Dispatch")
def primary_dispatch_node(state: GraphState) -> GraphState:
    """Enrich primary investigations with completed context reports.

    Runs after all context_device_subgraph instances have finished.
    Injects neighbor health-check findings into each primary investigation's
    device_context so the primary executor has full situational awareness.
    """
    enriched = _enrich_with_context_reports(
        state.primary_investigations, state
    )
    return replace(state, primary_investigations=enriched)


def dispatch_primary_investigations(
    state: GraphState,
) -> Union[List[Send], str]:
    """Fan out one Send per primary investigation, or skip to RCA.

    Used as a conditional edge from primary_dispatch_node. Returns a Send per
    primary device so LangGraph runs them all concurrently as separate
    primary_device_subgraph instances.
    """
    if not state.primary_investigations:
        logger.info("🔍 No primary investigations — skipping to RCA")
        return "rca_assessor_node"

    config = Configuration.from_context()
    logger.info(
        "🚀 Dispatching %s primary device sub-graph(s)",
        len(state.primary_investigations),
    )
    return [
        Send(
            "primary_device_subgraph",
            DeviceState(
                investigation=inv,
                trigger_context=state.trigger_context,
                investigation_role="primary",
                executor_prompt="network_executor",
                max_retries=config.max_retries_per_device,
                event_type=state.event_type,
            ),
        )
        for inv in state.primary_investigations
    ]


def _enrich_with_context_reports(
    investigations: List[Investigation], state: GraphState
) -> List[Investigation]:
    """Append completed context device reports to each primary investigation's context.

    Gives each primary executor agent full situational awareness of what
    the neighbor health checks found before it begins its own investigation.
    """
    completed_context = [
        inv
        for inv in state.completed_context_investigations
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
