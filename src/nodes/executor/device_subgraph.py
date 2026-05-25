"""
Per-device investigation sub-graph.

Encapsulates the plan → execute → assess → retry loop for a single device.
The outer graph dispatches one of these sub-graphs per device via Send,
running them concurrently within each phase (context, then primary).

Two compiled instances are exported so the parent graph can register them as
distinct named nodes and they appear as separate expandable boxes in Studio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List

from dataclasses import replace
from langgraph.graph import StateGraph, END

from schemas import Investigation
from schemas.assessment_schema import AssessmentOutput
from nodes.common.llm_utils import load_fast_model
from nodes.assessor.context import build_assessment_context
from nodes.assessor.assessment import execute_assessment
from nodes.planner.core import plan_single_device
from src.util.prompt_loader import load_prompt
from src.logging import get_logger

from .execution import execute_single_investigation

logger = get_logger(__name__)

_RETRY_DECISION_DONE = "done"
_RETRY_DECISION_RETRY = "execute_device"


@dataclass
class DeviceState:
    """State for the per-device investigation sub-graph.

    Attributes:
        investigation: The device investigation being executed.
        trigger_context: Original trigger content (user query, alert, or upstream agent).
        investigation_role: Whether this device is a "primary" (alert target) or
                            "context" (neighbor health check) investigation.
        executor_prompt: Name of the prompt file to use for execution
                         ("network_executor" for primary, "context_executor" for context).
        max_retries: Maximum number of execution attempts before giving up.
        current_retry: Number of assessment cycles completed so far.
        assessment: Latest assessment output, set after each assess_device run.
        event_type: Alert event type used for skill routing in plan_device.
        completed_context_investigations: Output field — written by collect_device_result
                                          when investigation_role is "context". Merged
                                          into GraphState via operator.add on sub-graph exit.
        completed_primary_investigations: Output field — written by collect_device_result
                                          when investigation_role is "primary". Merged
                                          into GraphState via operator.add on sub-graph exit.
    """

    investigation: Investigation
    trigger_context: str
    investigation_role: str = "primary"
    executor_prompt: str = "network_executor"
    max_retries: int = 3
    current_retry: int = 0
    assessment: Optional[AssessmentOutput] = None
    event_type: Optional[str] = None
    completed_context_investigations: List[Investigation] = field(
        default_factory=list
    )
    completed_primary_investigations: List[Investigation] = field(
        default_factory=list
    )


def plan_device(state: DeviceState) -> DeviceState:
    """Generate an investigation plan for this device.

    Raises if planning fails — the outer executor catches the exception and
    marks the investigation as failed, skipping execution entirely.
    """
    logger.info(
        "📋 Planning investigation for device: %s (role=%s)",
        state.investigation.device_name,
        state.investigation_role,
    )
    device_plan = plan_single_device(
        investigation=state.investigation,
        trigger_context=state.trigger_context,
        investigation_role=state.investigation_role,
        event_type=state.event_type,
    )
    updated_investigation = replace(
        state.investigation,
        objective=device_plan.objective,
        working_plan_steps=device_plan.working_plan_steps,
    )
    return replace(state, investigation=updated_investigation)


async def execute_device(state: DeviceState) -> DeviceState:
    """Run the MCP agent for a single device investigation."""
    logger.info(
        "🔁 Executing device (attempt %s/%s): %s",
        state.current_retry + 1,
        state.max_retries,
        state.investigation.device_name,
    )
    updated_investigation = await execute_single_investigation(
        investigation=state.investigation,
        trigger_context=state.trigger_context,
        executor_prompt=state.executor_prompt,
    )
    return replace(state, investigation=updated_investigation)


def assess_device(state: DeviceState) -> DeviceState:
    """Assess whether the device investigation objective has been achieved."""
    logger.info(
        "🔍 Assessing device investigation: %s",
        state.investigation.device_name,
    )
    assessment_context = build_assessment_context(
        state.investigation, state.trigger_context
    )
    model = load_fast_model()
    assessment = execute_assessment(
        model, assessment_context, load_prompt("objective_assessor")
    )
    logger.info(
        "📋 Assessment result for %s: achieved=%s",
        state.investigation.device_name,
        assessment.is_objective_achieved,
    )
    return replace(
        state,
        assessment=assessment,
        current_retry=state.current_retry + 1,
    )


def collect_device_result(state: DeviceState) -> DeviceState:
    """Write the completed investigation to the correct output field.

    Writes to completed_context_investigations or completed_primary_investigations
    based on investigation_role. LangGraph merges these into GraphState via
    operator.add reducers when the sub-graph exits.
    """
    logger.info(
        "📦 Collecting result for %s (role=%s)",
        state.investigation.device_name,
        state.investigation_role,
    )
    if state.investigation_role == "context":
        return replace(
            state,
            completed_context_investigations=[state.investigation],
        )
    return replace(
        state,
        completed_primary_investigations=[state.investigation],
    )


def should_retry(state: DeviceState) -> str:
    """Decide whether to retry execution or move to result collection.

    Returns done when the objective is achieved or retries are exhausted,
    otherwise signals another execution attempt.
    """
    if state.assessment and state.assessment.is_objective_achieved:
        logger.info(
            "✅ Objective achieved for %s — collecting result",
            state.investigation.device_name,
        )
        return _RETRY_DECISION_DONE

    if state.current_retry >= state.max_retries:
        logger.warning(
            "⚠️ Max retries (%s) reached for %s — collecting result",
            state.max_retries,
            state.investigation.device_name,
        )
        return _RETRY_DECISION_DONE

    logger.info(
        "🔄 Retrying investigation for %s (retry %s/%s)",
        state.investigation.device_name,
        state.current_retry,
        state.max_retries,
    )
    return _RETRY_DECISION_RETRY


def _build_device_subgraph() -> StateGraph:
    workflow = StateGraph(DeviceState)
    workflow.add_node("plan_device", plan_device)
    workflow.add_node("execute_device", execute_device)
    workflow.add_node("assess_device", assess_device)
    workflow.add_node("collect_device_result", collect_device_result)

    workflow.set_entry_point("plan_device")
    workflow.add_edge("plan_device", "execute_device")
    workflow.add_edge("execute_device", "assess_device")
    workflow.add_conditional_edges(
        "assess_device",
        should_retry,
        {_RETRY_DECISION_DONE: "collect_device_result", _RETRY_DECISION_RETRY: "execute_device"},
    )
    workflow.add_edge("collect_device_result", END)
    return workflow


context_device_subgraph = _build_device_subgraph().compile()
primary_device_subgraph = _build_device_subgraph().compile()
