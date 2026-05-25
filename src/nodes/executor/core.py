"""
Dispatch nodes and routing functions for the device sub-graph phases.

Each phase is split into two pieces:
1. A routing function (conditional edge) — returns a plain string so the
   routing decision is explicit and readable in logs and the Studio UI.
2. A dispatcher node — registered as a regular graph node, returns
   Command(goto=[Send(...)]) so LangGraph fans out the sub-graphs.

Context phase runs first (context_dispatcher → context_device_subgraph × N).
Primary phase runs second (primary_dispatcher → primary_device_subgraph × M),
after all context sub-graphs have merged their results into GraphState.
"""

from dataclasses import replace
from typing import List

from langgraph.types import Command, Send

from schemas import GraphState, Investigation
from src.configuration import Configuration
from src.logging import get_logger

from .context import build_primary_investigation_context
from .device_subgraph import DeviceState

logger = get_logger(__name__)

_CONTEXT_DISPATCHER = "context_dispatcher"
_PRIMARY_DISPATCHER = "primary_dispatcher"
_RCA_ASSESSOR = "rca_assessor_node"


def route_from_input_validator(state: GraphState) -> str:
    """Return the next node name after input validation.

    Conditional edge from input_validator_node. Returns a plain string so the
    routing decision is visible in Studio and easy to trace in logs.
    """
    if state.context_investigations:
        logger.info(
            "🔀 Routing to context phase (%s devices)",
            len(state.context_investigations),
        )
        return _CONTEXT_DISPATCHER

    if state.primary_investigations:
        logger.info(
            "🔀 No context investigations — routing directly to primary phase (%s devices)",
            len(state.primary_investigations),
        )
        return _PRIMARY_DISPATCHER

    logger.info("🔀 No investigations — routing to RCA assessor")
    return _RCA_ASSESSOR


def route_after_context_phase(state: GraphState) -> str:
    """Return the next node name after context investigations complete.

    Conditional edge from context_device_subgraph. Called once after all
    parallel context sub-graph instances finish and their results are merged
    into GraphState via the operator.add reducer.
    """
    if state.primary_investigations:
        logger.info(
            "🔀 Context phase done — routing to primary phase (%s devices)",
            len(state.primary_investigations),
        )
        return _PRIMARY_DISPATCHER

    logger.info("🔀 No primary investigations — routing to RCA assessor")
    return _RCA_ASSESSOR


def context_dispatcher(state: GraphState) -> Command:
    """Fan out one Send per context investigation.

    Registered as a regular graph node. Returns Command(goto=[Send(...)])
    so LangGraph creates one concurrent context_device_subgraph instance per
    context device.
    """
    config = Configuration.from_context()
    logger.info(
        "🚀 Dispatching %s context device sub-graph(s)",
        len(state.context_investigations),
    )
    sends = [
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
    return Command(goto=sends)


def primary_dispatcher(state: GraphState) -> Command:
    """Fan out one Send per primary investigation, enriched with context reports.

    Registered as a regular graph node. Returns Command(goto=[Send(...)])
    so LangGraph creates one concurrent primary_device_subgraph instance per
    primary device. Each DeviceState is enriched inline with completed context
    reports so the primary executor has full situational awareness.
    """
    config = Configuration.from_context()
    completed_context = _completed_context_reports(state)

    logger.info(
        "🚀 Dispatching %s primary device sub-graph(s)",
        len(state.primary_investigations),
    )
    sends = [
        Send(
            "primary_device_subgraph",
            DeviceState(
                investigation=replace(
                    inv,
                    device_context=build_primary_investigation_context(
                        inv.device_context, completed_context
                    ),
                ),
                trigger_context=state.trigger_context,
                investigation_role="primary",
                executor_prompt="network_executor",
                max_retries=config.max_retries_per_device,
                event_type=state.event_type,
            ),
        )
        for inv in state.primary_investigations
    ]
    return Command(goto=sends)


def _completed_context_reports(state: GraphState) -> List[Investigation]:
    return [inv for inv in state.completed_context_investigations if inv.report]
