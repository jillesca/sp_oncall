"""
Primary investigation sub-graph.

Encapsulates the plan → fan-out execute → collect → assess → retry loop for
primary (alert target) devices.  Uses the same Send-based fan-out pattern as
context_investigation for uniform code structure and Studio visibility.

Primary investigations typically cover a single device, so the fan-out
produces one Send instance most of the time — but the pattern handles
multiple primary devices correctly.

The context_phase_report is automatically mapped from GraphState by LangGraph
(matching field name), so the primary executor receives neighbor health check
findings without a separate enrichment node.

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

    device_reports uses _merge_dicts so parallel Send instances each write
    their own key without conflict, and retry waves overwrite the previous
    report for the same device.
    """

    primary_investigations: List[Investigation]
    trigger_context: str
    context_phase_report: str = ""
    event_type: Optional[str] = None
    max_retries: int = 3
    current_retry: int = 0
    assessment_passed: Optional[bool] = None
    assessor_feedback: str = ""
    completed_primary_investigations: List[Investigation] = field(
        default_factory=list
    )
    device_reports: Annotated[Dict[str, str], _merge_dicts] = field(default_factory=dict)


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


def fan_out_devices(state: PrimarySubgraphState) -> list[Send]:
    """Fan out one execute_device Send per primary device after planning.

    Raises if investigations are empty — that is a bug in the input validator,
    not a condition the planner is responsible for routing around.
    """
    if not state.primary_investigations:
        raise ValueError(
            "Primary investigations are empty — input validator must populate "
            "primary_investigations before the primary subgraph is called"
        )
    return _build_execute_sends(state)


async def execute_device(state: PrimarySubgraphState) -> dict:
    """Execute investigation for a single primary device.

    Receives a PrimarySubgraphState instance via Send (one device only).
    Returns a partial dict so LangGraph applies _merge_dicts on device_reports
    without touching any other parent-state fields.
    """
    investigation = state.primary_investigations[0]
    device_name = next(iter(investigation.device_contexts))

    logger.info(
        "🔁 Executing primary device %s (attempt %s/%s)",
        device_name,
        state.current_retry + 1,
        state.max_retries,
    )

    executed = await execute_investigations(
        investigation=investigation,
        trigger_context=state.trigger_context,
        executor_prompt=_EXECUTOR_PROMPT,
        context_phase_report=state.context_phase_report,
        assessor_feedback=state.assessor_feedback,
        attempt=state.current_retry + 1,
    )
    report = executed.report or f"Investigation incomplete for {device_name}"
    return {"device_reports": {device_name: report}}


def collect_device_result(state: PrimarySubgraphState) -> PrimarySubgraphState:
    """Aggregate per-device reports into the combined phase investigation.

    Reads device_reports (populated by parallel execute_device Send instances),
    concatenates them into a combined report, and stores the updated Investigation
    in completed_primary_investigations for the reporter and RCA assessor.
    Also updates primary_investigations[0].report so assess_device can evaluate
    the combined output against the per-device objectives.
    """
    if not state.primary_investigations:
        logger.warning("⚠️ No primary investigation to collect")
        return state

    investigation = state.primary_investigations[0]
    logger.info(
        "📦 Collecting primary investigation results for %s device(s)",
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
        primary_investigations=[updated_investigation],
        completed_primary_investigations=[updated_investigation],
    )


def assess_device(state: PrimarySubgraphState) -> PrimarySubgraphState:
    """Assess whether all primary device objectives have been achieved."""
    if not state.primary_investigations:
        logger.warning("⚠️ No primary investigation found — marking as passed")
        return replace(state, assessment_passed=True)

    passed, feedback, retry_count = assess_investigations(
        investigation=state.primary_investigations[0],
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


def should_retry(state: PrimarySubgraphState) -> str | list[Send]:
    """Route to END when done, or fan out a new execute_device wave on retry."""
    if state.assessment_passed:
        logger.info("✅ Primary phase objective achieved — ending subgraph")
        return END

    if state.current_retry >= state.max_retries:
        logger.warning(
            "⚠️ Max retries (%s) reached — ending subgraph", state.max_retries
        )
        return END

    logger.info(
        "🔄 Primary phase objective not met — retrying (attempt %s/%s)",
        state.current_retry + 1,
        state.max_retries,
    )
    return _build_execute_sends(state)


def _build_execute_sends(state: PrimarySubgraphState) -> list[Send]:
    """Create one Send per primary device using the current state.

    Passes a PrimarySubgraphState instance (not a dict) so execute_device
    receives the correct type — LangGraph forwards the Send arg as-is to the
    node without any type conversion.
    """
    investigation = state.primary_investigations[0]
    return [
        Send(
            "execute_device",
            PrimarySubgraphState(
                primary_investigations=[slice_investigation(investigation, device_name)],
                trigger_context=state.trigger_context,
                context_phase_report=state.context_phase_report,
                assessor_feedback=state.assessor_feedback,
                current_retry=state.current_retry,
                max_retries=state.max_retries,
            ),
        )
        for device_name in investigation.device_contexts
    ]


_workflow = StateGraph(PrimarySubgraphState)
_workflow.add_node("plan_device", plan_device)
_workflow.add_node("execute_device", execute_device)
_workflow.add_node("collect_device_result", collect_device_result)
_workflow.add_node("assess_device", assess_device)

_workflow.set_entry_point("plan_device")
_workflow.add_conditional_edges("plan_device", fan_out_devices, ["execute_device"])
_workflow.add_edge("execute_device", "collect_device_result")
_workflow.add_edge("collect_device_result", "assess_device")
_workflow.add_conditional_edges("assess_device", should_retry, ["execute_device", END])

primary_investigation_subgraph = _workflow.compile()
