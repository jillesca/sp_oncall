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
from typing import List, Optional, Tuple

from nodes.assessor.context import build_phase_assessment_context
from nodes.assessor.assessment import execute_assessment
from nodes.common import load_fast_model
from nodes.planner.core import plan_single_device
from schemas import Investigation, InvestigationStatus
from schemas.assessment_schema import AssessmentOutput
from src.util.prompt_loader import load_prompt
from src.util.prompt_logger import log_prompt
from src.logging import get_logger

from .execution import execute_phase_investigations

logger = get_logger(__name__)

_RETRY_DECISION_DONE = "collect_device_result"
_RETRY_DECISION_RETRY = "execute_device"


def plan_investigations(
    investigations: List[Investigation],
    trigger_context: str,
    investigation_role: str,
    event_type: Optional[str],
) -> List[Investigation]:
    """Generate investigation plans for every device in the phase.

    Planning is sequential within this node; each device gets its own tailored
    objective and step list before the phase executor agent is invoked.
    Failures per device are caught individually so one bad device doesn't
    block the rest of the phase.
    """
    planned = []
    for inv in investigations:
        try:
            device_plan = plan_single_device(
                investigation=inv,
                trigger_context=trigger_context,
                investigation_role=investigation_role,
                event_type=event_type,
            )
            planned.append(
                replace(
                    inv,
                    objective=device_plan.objective,
                    working_plan_steps=device_plan.working_plan_steps,
                )
            )
        except Exception as e:
            logger.error(
                "❌ Planning failed for %s: %s — marking as failed",
                inv.device_name,
                e,
            )
            planned.append(
                replace(inv, status=InvestigationStatus.FAILED, error_details=str(e))
            )
    return planned


async def execute_investigations(
    investigations: List[Investigation],
    trigger_context: str,
    executor_prompt: str,
    attempt: int = 1,
) -> List[Investigation]:
    """Run one MCP agent for all devices in the phase (Option B).

    Passes combined device context to a single agent call so the agent can
    investigate all N devices and produce consolidated findings.
    Only non-failed investigations are sent to the agent; already-failed ones
    pass through unchanged.
    """
    active = [inv for inv in investigations if inv.status != InvestigationStatus.FAILED]
    failed = [inv for inv in investigations if inv.status == InvestigationStatus.FAILED]

    if not active:
        logger.warning("⚠️ All investigations already failed — skipping execution")
        return investigations

    executed = await execute_phase_investigations(
        investigations=active,
        trigger_context=trigger_context,
        executor_prompt=executor_prompt,
        attempt=attempt,
    )
    return executed + failed


def assess_investigations(
    investigations: List[Investigation],
    trigger_context: str,
    current_retry: int,
    phase_name: str = "unknown",
) -> Tuple[AssessmentOutput, int]:
    """Assess whether the phase objective has been achieved for all devices.

    Builds a combined assessment context from all investigations and runs a
    single LLM call to determine if the phase is done.

    Returns:
        Tuple of (assessment result, incremented retry counter).
    """
    logger.info(
        "🔍 Assessing phase (%s device(s), retry %s)",
        len(investigations),
        current_retry,
    )
    assessment_context = build_phase_assessment_context(investigations, trigger_context)
    model = load_fast_model()
    system_prompt = load_prompt("objective_assessor")

    log_prompt(
        node_name=f"objective_assessor_{phase_name}",
        system_prompt=system_prompt,
        human_message=assessment_context,
        attempt=current_retry + 1,
    )

    assessment = execute_assessment(model, assessment_context, system_prompt)
    logger.info(
        "📋 Phase assessment: achieved=%s",
        assessment.is_objective_achieved,
    )
    return assessment, current_retry + 1


def decide_retry(
    assessment: Optional[AssessmentOutput],
    current_retry: int,
    max_retries: int,
) -> str:
    """Return the next node name based on the assessment outcome.

    Returns _RETRY_DECISION_DONE when the objective is achieved or retries are
    exhausted; returns _RETRY_DECISION_RETRY to trigger another execution pass.
    """
    if assessment and assessment.is_objective_achieved:
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
