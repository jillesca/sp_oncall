"""
Context investigation sub-graph.

Encapsulates the plan → fan-out execute → collect → assess → retry loop for
context (neighbor) devices.  Each device gets its own dedicated execute_device
invocation via LangGraph Send so the LLM never mixes results across devices.

Graph flow:
  plan_device
    → fan_out_devices (conditional, returns one Send per device)
    → execute_device  (parallel, one instance per device)
    → collect_device_result
    → assess_device
    → should_retry (conditional)
        → END              when objective met or max retries reached
        → execute_device   via Send fan-out on retry

Exported as a compiled sub-graph that the parent graph adds as a node
(subgraph-as-node pattern).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Annotated, Dict, List, Optional

from langgraph.graph import StateGraph, END
from langgraph.types import Send

from schemas import Investigation, InvestigationStatus
from src.logging import get_logger

from .phase import (
    plan_investigations,
    execute_investigations,
    assess_investigations,
    slice_investigation,
    _merge_dicts,
)

logger = get_logger(__name__)

_INVESTIGATION_ROLE = "context"
_EXECUTOR_PROMPT = "context_executor"


@dataclass
class ContextSubgraphState:
    """State for the context investigation sub-graph.

    Field names match GraphState so LangGraph automatically maps them when
    this compiled sub-graph is used as a node in the parent graph:
      - context_investigations    ← read from parent (set by input_validator)
      - trigger_context           ← read from parent (property → field mapping)
      - event_type                ← read from parent
      - context_device_names      → written to parent
      - context_phase_report      → written to parent (combined executor output)
      - context_device_reports    → written to parent (per-device reports for history)

    device_reports uses _merge_dicts so parallel Send instances each write
    their own key without conflict, and retry waves overwrite the previous
    report for the same device.
    """

    context_investigations: List[Investigation]
    trigger_context: str
    event_type: Optional[str] = None
    max_retries: int = 3
    current_retry: int = 0
    assessment_passed: Optional[bool] = None
    assessor_feedback: str = ""
    context_device_names: List[str] = field(default_factory=list)
    context_phase_report: str = ""
    context_device_reports: Dict[str, str] = field(default_factory=dict)
    device_reports: Annotated[Dict[str, str], _merge_dicts] = field(default_factory=dict)


def plan_device(state: ContextSubgraphState) -> ContextSubgraphState:
    """Generate investigation plans for all context devices."""
    if not state.context_investigations:
        logger.warning("⚠️ No context investigation found — skipping planning")
        return state

    logger.info(
        "📋 Planning context phase for %s device(s)",
        len(state.context_investigations[0].device_contexts),
    )
    planned = plan_investigations(
        investigation=state.context_investigations[0],
        trigger_context=state.trigger_context,
        investigation_role=_INVESTIGATION_ROLE,
        event_type=state.event_type,
    )
    return replace(state, context_investigations=[planned])


def fan_out_devices(state: ContextSubgraphState) -> list[Send]:
    """Fan out one execute_device Send per context device after planning.

    Raises if investigations are empty — that is a bug in the input validator,
    not a condition the planner is responsible for routing around.
    """
    if not state.context_investigations:
        raise ValueError(
            "Context investigations are empty — input validator must populate "
            "context_investigations before the context subgraph is called"
        )
    return _build_execute_sends(state)


async def execute_device(state: ContextSubgraphState) -> dict:
    """Execute investigation for a single context device.

    Receives a ContextSubgraphState instance via Send (one device only).
    Returns a partial dict so LangGraph applies _merge_dicts on device_reports
    without touching any other parent-state fields.
    """
    investigation = state.context_investigations[0]
    device_name = next(iter(investigation.device_contexts))

    logger.info(
        "🔁 Executing context device %s (attempt %s/%s)",
        device_name,
        state.current_retry + 1,
        state.max_retries,
    )

    executed = await execute_investigations(
        investigation=investigation,
        trigger_context=state.trigger_context,
        executor_prompt=_EXECUTOR_PROMPT,
        assessor_feedback=state.assessor_feedback,
        attempt=state.current_retry + 1,
    )
    report = executed.report or f"Investigation incomplete for {device_name}"
    return {"device_reports": {device_name: report}}


def collect_device_result(state: ContextSubgraphState) -> ContextSubgraphState:
    """Aggregate per-device reports into the combined phase report.

    Reads device_reports (populated by parallel execute_device Send instances),
    concatenates them into context_phase_report, and surfaces context_device_reports
    so the reporter can persist each device's own report in its history.
    Updates context_investigations[0].report so assess_device can evaluate
    the combined output against the per-device objectives.
    """
    if not state.context_investigations:
        logger.warning("⚠️ No context investigation to collect")
        return state

    investigation = state.context_investigations[0]
    logger.info(
        "📦 Collecting context investigation results for %s device(s)",
        len(state.device_reports),
    )

    combined_report = "\n\n".join(state.device_reports.values())
    updated_investigation = replace(
        investigation,
        report=combined_report,
        status=InvestigationStatus.COMPLETED,
    )

    return replace(
        state,
        context_investigations=[updated_investigation],
        context_phase_report=combined_report,
        context_device_names=list(state.device_reports.keys()),
        context_device_reports=state.device_reports,
    )


def assess_device(state: ContextSubgraphState) -> ContextSubgraphState:
    """Assess whether all context device objectives have been achieved."""
    if not state.context_investigations:
        logger.warning("⚠️ No context investigation found — marking as passed")
        return replace(state, assessment_passed=True)

    passed, feedback, retry_count = assess_investigations(
        investigation=state.context_investigations[0],
        trigger_context=state.trigger_context,
        current_retry=state.current_retry,
        phase_name=_INVESTIGATION_ROLE,
    )
    return replace(
        state,
        assessment_passed=passed,
        assessor_feedback=feedback,
        current_retry=retry_count,
    )


def should_retry(state: ContextSubgraphState) -> str | list[Send]:
    """Route to END when done, or fan out a new execute_device wave on retry."""
    if state.assessment_passed:
        logger.info("✅ Context phase objective achieved — ending subgraph")
        return END

    if state.current_retry >= state.max_retries:
        logger.warning(
            "⚠️ Max retries (%s) reached — ending subgraph", state.max_retries
        )
        return END

    logger.info(
        "🔄 Context phase objective not met — retrying (attempt %s/%s)",
        state.current_retry + 1,
        state.max_retries,
    )
    return _build_execute_sends(state)


def _build_execute_sends(state: ContextSubgraphState) -> list[Send]:
    """Create one Send per context device using the current state.

    Passes a ContextSubgraphState instance (not a dict) so execute_device
    receives the correct type — LangGraph forwards the Send arg as-is to the
    node without any type conversion.
    """
    investigation = state.context_investigations[0]
    return [
        Send(
            "execute_device",
            ContextSubgraphState(
                context_investigations=[slice_investigation(investigation, device_name)],
                trigger_context=state.trigger_context,
                assessor_feedback=state.assessor_feedback,
                current_retry=state.current_retry,
                max_retries=state.max_retries,
            ),
        )
        for device_name in investigation.device_contexts
    ]


_workflow = StateGraph(ContextSubgraphState)
_workflow.add_node("plan_device", plan_device)
_workflow.add_node("execute_device", execute_device)
_workflow.add_node("collect_device_result", collect_device_result)
_workflow.add_node("assess_device", assess_device)

_workflow.set_entry_point("plan_device")
_workflow.add_conditional_edges("plan_device", fan_out_devices, ["execute_device"])
_workflow.add_edge("execute_device", "collect_device_result")
_workflow.add_edge("collect_device_result", "assess_device")
_workflow.add_conditional_edges("assess_device", should_retry, ["execute_device", END])

context_investigation_subgraph = _workflow.compile()
