"""
Primary investigation sub-graph and pre-investigation enrichment.

Encapsulates the plan → execute → assess → retry loop for ALL primary devices
(usually one) in a single sub-graph instance.  Before the sub-graph is invoked,
the parent graph runs enrich_primary_investigations to inject context phase
findings into each primary investigation's device context.

Exported:
  - primary_investigation_subgraph : compiled sub-graph (subgraph-as-node)
  - enrich_primary_investigations  : parent-graph node (runs before the sub-graph)
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import List, Optional

from langgraph.graph import StateGraph, END

from schemas import GraphState, Investigation
from schemas.assessment_schema import AssessmentOutput
from src.logging import get_logger

from .context import build_primary_investigation_context
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
      - primary_investigations          ← read from parent (already enriched)
      - trigger_context                 ← read from parent
      - event_type                      ← read from parent
      - completed_primary_investigations → merged into parent via operator.add
    """

    primary_investigations: List[Investigation]
    trigger_context: str
    event_type: Optional[str] = None
    max_retries: int = 3
    current_retry: int = 0
    assessment: Optional[AssessmentOutput] = None
    completed_primary_investigations: List[Investigation] = field(
        default_factory=list
    )


def plan_device(state: PrimarySubgraphState) -> PrimarySubgraphState:
    """Generate investigation plans for all primary devices."""
    logger.info(
        "📋 Planning primary phase for %s device(s)",
        len(state.primary_investigations),
    )
    planned = plan_investigations(
        investigations=state.primary_investigations,
        trigger_context=state.trigger_context,
        investigation_role=_INVESTIGATION_ROLE,
        event_type=state.event_type,
    )
    return replace(state, primary_investigations=planned)


async def execute_device(state: PrimarySubgraphState) -> PrimarySubgraphState:
    """Run one MCP agent for all primary devices."""
    logger.info(
        "🔁 Executing primary phase (attempt %s/%s)",
        state.current_retry + 1,
        state.max_retries,
    )
    executed = await execute_investigations(
        investigations=state.primary_investigations,
        trigger_context=state.trigger_context,
        executor_prompt=_EXECUTOR_PROMPT,
    )
    return replace(state, primary_investigations=executed)


def assess_device(state: PrimarySubgraphState) -> PrimarySubgraphState:
    """Assess whether all primary device objectives have been achieved."""
    assessment, retry_count = assess_investigations(
        investigations=state.primary_investigations,
        trigger_context=state.trigger_context,
        current_retry=state.current_retry,
    )
    return replace(state, assessment=assessment, current_retry=retry_count)


def collect_device_result(state: PrimarySubgraphState) -> PrimarySubgraphState:
    """Write completed investigations to the output field.

    LangGraph merges completed_primary_investigations into GraphState via the
    operator.add reducer when this sub-graph exits.
    """
    logger.info(
        "📦 Collecting %s primary investigation result(s)",
        len(state.primary_investigations),
    )
    return replace(
        state,
        completed_primary_investigations=state.primary_investigations,
    )


def should_retry(state: PrimarySubgraphState) -> str:
    """Decide whether to retry execution or proceed to result collection."""
    return decide_retry(state.assessment, state.current_retry, state.max_retries)


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


def enrich_primary_investigations(state: GraphState) -> GraphState:
    """Inject completed context findings into each primary investigation's device context.

    Runs as a regular parent-graph node between context_investigation and
    primary_investigation.  This gives the primary executor full situational
    awareness of what the context phase discovered about the network neighbors
    before it starts planning and executing.
    """
    completed_context = [
        inv for inv in state.completed_context_investigations if inv.report
    ]
    if not completed_context:
        logger.info("ℹ️ No context findings to inject into primary investigations")
        return state

    logger.info(
        "🔗 Enriching %s primary investigation(s) with %s context report(s)",
        len(state.primary_investigations),
        len(completed_context),
    )

    enriched = [
        replace(
            inv,
            device_context=build_primary_investigation_context(
                inv.device_context, completed_context
            ),
        )
        for inv in state.primary_investigations
    ]
    return replace(state, primary_investigations=enriched)
