"""
Context investigation sub-graph.

Encapsulates the plan → execute → assess → retry loop for ALL context devices
in a single sub-graph instance.  One MCP agent call handles every context
device so the agent can investigate them holistically.

Exported as a compiled sub-graph that the parent graph adds as a node
(subgraph-as-node pattern).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import List, Optional

from langgraph.graph import StateGraph, END

from schemas import Investigation
from schemas.assessment_schema import AssessmentOutput
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

_INVESTIGATION_ROLE = "context"
_EXECUTOR_PROMPT = "context_executor"


@dataclass
class ContextSubgraphState:
    """State for the context investigation sub-graph.

    Field names match GraphState so LangGraph automatically maps them when
    this compiled sub-graph is used as a node in the parent graph:
      - context_investigations   ← read from parent (set by input_validator)
      - trigger_context          ← read from parent
      - event_type               ← read from parent
      - completed_context_investigations → merged into parent via operator.add
    """

    context_investigations: List[Investigation]
    trigger_context: str
    event_type: Optional[str] = None
    max_retries: int = 3
    current_retry: int = 0
    assessment: Optional[AssessmentOutput] = None
    completed_context_investigations: List[Investigation] = field(
        default_factory=list
    )


def plan_device(state: ContextSubgraphState) -> ContextSubgraphState:
    """Generate investigation plans for all context devices."""
    logger.info(
        "📋 Planning context phase for %s device(s)",
        len(state.context_investigations),
    )
    planned = plan_investigations(
        investigations=state.context_investigations,
        trigger_context=state.trigger_context,
        investigation_role=_INVESTIGATION_ROLE,
        event_type=state.event_type,
    )
    return replace(state, context_investigations=planned)


async def execute_device(state: ContextSubgraphState) -> ContextSubgraphState:
    """Run one MCP agent for all context devices (attempt %s)."""
    logger.info(
        "🔁 Executing context phase (attempt %s/%s)",
        state.current_retry + 1,
        state.max_retries,
    )
    executed = await execute_investigations(
        investigations=state.context_investigations,
        trigger_context=state.trigger_context,
        executor_prompt=_EXECUTOR_PROMPT,
    )
    return replace(state, context_investigations=executed)


def assess_device(state: ContextSubgraphState) -> ContextSubgraphState:
    """Assess whether all context device objectives have been achieved."""
    assessment, retry_count = assess_investigations(
        investigations=state.context_investigations,
        trigger_context=state.trigger_context,
        current_retry=state.current_retry,
    )
    return replace(state, assessment=assessment, current_retry=retry_count)


def collect_device_result(state: ContextSubgraphState) -> ContextSubgraphState:
    """Write completed investigations to the output field.

    LangGraph merges completed_context_investigations into GraphState via the
    operator.add reducer when this sub-graph exits.
    """
    logger.info(
        "📦 Collecting %s context investigation result(s)",
        len(state.context_investigations),
    )
    return replace(
        state,
        completed_context_investigations=state.context_investigations,
    )


def should_retry(state: ContextSubgraphState) -> str:
    """Decide whether to retry execution or proceed to result collection."""
    return decide_retry(state.assessment, state.current_retry, state.max_retries)


_workflow = StateGraph(ContextSubgraphState)
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

context_investigation_subgraph = _workflow.compile()
