"""
Per-device investigation sub-graph.

Encapsulates the execute → assess → retry loop for a single device.
The outer executor runs one of these sub-graphs per device, concurrently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from dataclasses import replace
from langgraph.graph import StateGraph, END

from schemas import Investigation
from schemas.assessment_schema import AssessmentOutput
from nodes.common.llm_utils import load_model
from nodes.assessor.context import build_assessment_context
from nodes.assessor.assessment import execute_assessment
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
        max_retries: Maximum number of execution attempts before giving up.
        current_retry: Number of assessment cycles completed so far.
        assessment: Latest assessment output, set after each assess_device run.
    """

    investigation: Investigation
    trigger_context: str
    max_retries: int = 3
    current_retry: int = 0
    assessment: Optional[AssessmentOutput] = None


async def execute_device(state: DeviceState) -> DeviceState:
    """Run the MCP agent for a single device investigation."""
    logger.info(
        "🔁 Executing device (attempt %s/%s): %s",
        state.current_retry + 1,
        state.max_retries,
        state.investigation.device_name,
    )
    updated_investigation = await execute_single_investigation(
        state.investigation, state.trigger_context
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
    model = load_model()
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


def should_retry(state: DeviceState) -> str:
    """Decide whether to retry execution or finish.

    Returns done when the objective is achieved or retries are exhausted,
    otherwise signals another execution attempt.
    """
    if state.assessment and state.assessment.is_objective_achieved:
        logger.info(
            "✅ Objective achieved for %s — finishing sub-graph",
            state.investigation.device_name,
        )
        return _RETRY_DECISION_DONE

    if state.current_retry >= state.max_retries:
        logger.warning(
            "⚠️ Max retries (%s) reached for %s — finishing sub-graph",
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


_workflow = StateGraph(DeviceState)
_workflow.add_node("execute_device", execute_device)
_workflow.add_node("assess_device", assess_device)

_workflow.set_entry_point("execute_device")
_workflow.add_edge("execute_device", "assess_device")
_workflow.add_conditional_edges(
    "assess_device",
    should_retry,
    {_RETRY_DECISION_DONE: END, _RETRY_DECISION_RETRY: "execute_device"},
)

device_subgraph = _workflow.compile()
