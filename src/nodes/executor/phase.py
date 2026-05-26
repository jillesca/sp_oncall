"""
Shared helpers for phase-level investigation nodes.

Both context_investigation and primary_investigation sub-graphs expose the
same four nodes (plan_device, execute_device, assess_device,
collect_device_result) and the same retry routing.  The state schemas differ
by field name so that LangGraph can automatically map them to/from GraphState,
but the implementation logic is identical — so it lives here once.

Each sub-graph imports the helpers it needs and wraps them in thin
state-specific functions.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional, Tuple

from nodes.assessor.context import build_phase_assessment_context
from nodes.assessor.assessment import execute_assessment
from nodes.common import load_fast_model
from nodes.planner.core import plan_single_device
from schemas import Investigation, InvestigationStatus
from src.util.prompt_loader import load_prompt
from src.util.prompt_logger import log_prompt
from src.util.xml_helpers import xml_wrap
from src.logging import get_logger

from .execution import execute_phase_investigations

logger = get_logger(__name__)

_RETRY_DECISION_DONE = "collect_device_result"
_RETRY_DECISION_RETRY = "execute_device"


def plan_investigations(
    investigation: Investigation,
    trigger_context: str,
    investigation_role: str,
    event_type: Optional[str],
) -> Investigation:
    """Generate investigation plans for every device in the phase.

    Planning is sequential within this node; each device gets its own tailored
    objective and step list before the phase executor agent is invoked.
    Failures per device are caught individually so one bad device doesn't
    block the rest of the phase.
    """
    device_plans = {}
    any_succeeded = False

    for device_name, device_context in investigation.device_contexts.items():
        try:
            device_plan = plan_single_device(
                device_name=device_name,
                device_context=device_context,
                trigger_context=trigger_context,
                investigation_role=investigation_role,
                event_type=event_type,
            )
            device_plans[device_name] = _format_device_plan(device_plan)
            any_succeeded = True
        except Exception as e:
            logger.error(
                "❌ Planning failed for %s: %s — skipping device plan",
                device_name,
                e,
            )
            device_plans[device_name] = ""

    if not any_succeeded:
        return replace(
            investigation,
            status=InvestigationStatus.FAILED,
            error_details="All device plans failed during planning phase",
        )

    return replace(investigation, device_plans=device_plans)


async def execute_investigations(
    investigation: Investigation,
    trigger_context: str,
    executor_prompt: str,
    context_phase_report: str = "",
    assessor_feedback: str = "",
    attempt: int = 1,
) -> Investigation:
    """Run one MCP agent for all devices in the phase.

    Passes combined device context to a single agent call so the agent can
    investigate all N devices and produce consolidated findings.
    Skips execution if the investigation is already marked as failed.

    When assessor_feedback is provided (on a retry), it is injected into the
    executor context so the agent can address the specific gap identified by
    the assessor rather than repeating the same investigation.
    """
    if investigation.status == InvestigationStatus.FAILED:
        logger.warning("⚠️ Investigation already failed — skipping execution")
        return investigation

    return await execute_phase_investigations(
        investigation=investigation,
        trigger_context=trigger_context,
        executor_prompt=executor_prompt,
        context_phase_report=context_phase_report,
        assessor_feedback=assessor_feedback,
        attempt=attempt,
    )


def assess_investigations(
    investigation: Investigation,
    trigger_context: str,
    current_retry: int,
    phase_name: str = "unknown",
) -> Tuple[bool, str, int]:
    """Assess whether the phase objective has been achieved for all devices.

    Builds a combined assessment context from the investigation and runs a
    single LLM call to determine if the phase is done.

    Returns:
        Tuple of (objective_achieved, assessor_feedback, incremented retry counter).
        assessor_feedback is non-empty only when objective_achieved is False.
    """
    logger.info(
        "🔍 Assessing phase (%s device(s), retry %s)",
        len(investigation.device_contexts),
        current_retry,
    )
    assessment_context = build_phase_assessment_context(investigation, trigger_context)
    model = load_fast_model()
    system_prompt = load_prompt("objective_assessor")

    log_prompt(
        node_name=f"objective_assessor_{phase_name}",
        system_prompt=system_prompt,
        human_message=assessment_context,
        attempt=current_retry + 1,
    )

    objective_achieved, reason = execute_assessment(model, assessment_context, system_prompt)
    logger.info(
        "📋 Phase assessment: achieved=%s reason=%s",
        objective_achieved,
        reason,
    )
    return objective_achieved, reason, current_retry + 1


def decide_retry(
    assessment_passed: Optional[bool],
    current_retry: int,
    max_retries: int,
) -> str:
    """Return the next node name based on the assessment outcome.

    Returns _RETRY_DECISION_DONE when the objective is achieved or retries are
    exhausted; returns _RETRY_DECISION_RETRY to trigger another execution pass.
    """
    if assessment_passed:
        logger.info("✅ Phase objective achieved — collecting results")
        return _RETRY_DECISION_DONE

    if current_retry >= max_retries:
        logger.warning(
            "⚠️ Max retries (%s) reached — collecting results", max_retries
        )
        return _RETRY_DECISION_DONE

    logger.info(
        "🔄 Phase objective not yet achieved — retrying (retry %s/%s)",
        current_retry,
        max_retries,
    )
    return _RETRY_DECISION_RETRY


def _format_device_plan(device_plan) -> str:
    """Format a DevicePlan as plain text for injection into the executor prompt."""
    parts = [f"**Objective:** {device_plan.objective}"]
    if device_plan.working_plan_steps:
        parts.append(xml_wrap("WORKING_PLAN", device_plan.working_plan_steps))
    return "\n\n".join(parts)
