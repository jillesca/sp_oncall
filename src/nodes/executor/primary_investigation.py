"""
Primary investigation sub-graph.

Encapsulates the plan → execute → assess → retry loop for ALL primary devices
in a single sub-graph instance.  One MCP agent call handles every primary
device so the agent can investigate them holistically.

The context_phase_report is automatically mapped from GraphState by LangGraph
(matching field name), so the primary executor receives neighbor health check
findings without a separate enrichment node.

Exported as a compiled sub-graph that the parent graph adds as a node
(subgraph-as-node pattern).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import List, Optional

from langgraph.graph import StateGraph, END

from schemas import Investigation
from src.logging import get_logger

from .phase import (
    plan_investigations,
    execute_investigations,
    assess_investigations,
    decide_retry,
    _RETRY_DECISION_DONE,
    _RETRY_DECISION_RETRY,
)

logger = get_logger(__name__)

_INVESTIGATION_ROLE = "primary"
_EXECUTOR_PROMPT = "network_executor"


@dataclass
class PrimarySubgraphState:
    """State for the primary investigation sub-graph.

    Field names match GraphState so LangGraph automatically maps them when
    this compiled sub-graph is used as a node in the parent graph:
      - primary_investigations          ← read from parent (already set)
      - trigger_context                 ← read from parent (property → field mapping)
      - context_phase_report            ← read from parent (neighbor findings)
      - event_type                      ← read from parent
      - completed_primary_investigations → written to parent via replace-wins reducer
    """

    primary_investigations: List[Investigation]
    trigger_context: str
    context_phase_report: str = ""
    event_type: Optional[str] = None
    max_retries: int = 3
    current_retry: int = 0
    assessment_passed: Optional[bool] = None
    completed_primary_investigations: List[Investigation] = field(
        default_factory=list
    )


def plan_device(state: PrimarySubgraphState) -> PrimarySubgraphState:
    """Generate investigation plans for all primary devices."""
    if not state.primary_investigations:
        logger.warning("⚠️ No primary investigation found — skipping planning")
        return state

    logger.info(
        "📋 Planning primary phase for %s device(s)",
        len(state.primary_investigations[0].device_contexts),
    )
    planned = plan_investigations(
        investigation=state.primary_investigations[0],
        trigger_context=state.trigger_context,
        investigation_role=_INVESTIGATION_ROLE,
        event_type=state.event_type,
    )
    return replace(state, primary_investigations=[planned])


async def execute_device(state: PrimarySubgraphState) -> PrimarySubgraphState:
    """Run one MCP agent for all primary devices."""
    if not state.primary_investigations:
        logger.warning("⚠️ No primary investigation found — skipping execution")
        return state

    logger.info(
        "🔁 Executing primary phase (attempt %s/%s)",
        state.current_retry + 1,
        state.max_retries,
    )
    executed = await execute_investigations(
        investigation=state.primary_investigations[0],
        trigger_context=state.trigger_context,
        executor_prompt=_EXECUTOR_PROMPT,
        context_phase_report=state.context_phase_report,
        attempt=state.current_retry + 1,
    )
    return replace(state, primary_investigations=[executed])


def assess_device(state: PrimarySubgraphState) -> PrimarySubgraphState:
    """Assess whether all primary device objectives have been achieved."""
    if not state.primary_investigations:
        logger.warning("⚠️ No primary investigation found — marking as passed")
        return replace(state, assessment_passed=True)

    passed, retry_count = assess_investigations(
        investigation=state.primary_investigations[0],
        trigger_context=state.trigger_context,
        current_retry=state.current_retry,
        phase_name=_INVESTIGATION_ROLE,
    )
    return replace(state, assessment_passed=passed, current_retry=retry_count)


def collect_device_result(state: PrimarySubgraphState) -> PrimarySubgraphState:
    """Write completed investigation to the output field.

    LangGraph merges completed_primary_investigations into GraphState via the
    replace-wins reducer when this sub-graph exits.
    """
    if not state.primary_investigations:
        logger.warning("⚠️ No primary investigation to collect")
        return state

    investigation = state.primary_investigations[0]
    logger.info(
        "📦 Collecting primary investigation result for %s device(s)",
        len(investigation.device_contexts),
    )
    return replace(
        state,
        completed_primary_investigations=state.primary_investigations,
    )


def should_retry(state: PrimarySubgraphState) -> str:
    """Decide whether to retry execution or proceed to result collection."""
    return decide_retry(state.assessment_passed, state.current_retry, state.max_retries)


_workflow = StateGraph(PrimarySubgraphState)
_workflow.add_node("plan_device", plan_device)
_workflow.add_node("execute_device", execute_device)
_workflow.add_node("assess_device", assess_device)
_workflow.add_node("collect_device_result", collect_device_result)

_workflow.set_entry_point("plan_device")
_workflow.add_edge("plan_device", "execute_device")
_workflow.add_edge("execute_device", "assess_device")
_workflow.add_conditional_edges(
    "assess_device",
    should_retry,
    {_RETRY_DECISION_DONE: "collect_device_result", _RETRY_DECISION_RETRY: "execute_device"},
)
_workflow.add_edge("collect_device_result", END)

primary_investigation_subgraph = _workflow.compile()
