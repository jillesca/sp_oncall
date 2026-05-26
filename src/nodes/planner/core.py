"""
Per-device planning logic.

Generates a tailored investigation plan for a single device by loading
relevant skills, invoking the LLM, and parsing the structured response.
Called from the per-device loop inside phase.plan_investigations.
"""

from typing import Optional

from src.logging import get_logger
from nodes.common import load_model, load_fast_model
from src.util.prompt_loader import load_prompt
from src.util.prompt_logger import log_prompt
from src.util.xml_helpers import xml_wrap

from .planning import (
    DevicePlan,
    load_available_skills,
    execute_plan_selection,
    process_device_plan_response,
)
from .context import build_planning_context

logger = get_logger(__name__)


def plan_single_device(
    device_name: str,
    device_context: str,
    trigger_context: str,
    investigation_role: str = "primary",
    event_type: Optional[str] = None,
) -> DevicePlan:
    """Generate an investigation plan for a single device.

    Args:
        device_name: Target device identifier.
        device_context: Pre-formatted device context string assembled by the
                        input validator (facts, capabilities, history).
        trigger_context: Original trigger content (alert or user request).
        investigation_role: "primary" for alert targets, "context" for neighbor
                            checks. Shapes the planning objective.
        event_type: Alert event type used to filter relevant skills.
                    None for manual queries (loads all skills).

    Returns:
        A DevicePlan with objective and step-by-step instructions for this device.

    Raises:
        Exception: If plan generation fails — callers should handle and skip
                   this device's plan.
    """
    logger.info(
        "📋 Planning for device: %s (investigation_role=%s)",
        device_name,
        investigation_role,
    )

    available_skills = load_available_skills(event_type)
    model = load_model()
    fast_model = load_fast_model()
    planning_context = build_planning_context(
        device_name, device_context, trigger_context, investigation_role
    )
    system_prompt = load_prompt("planner")

    human_message = "\n\n".join(
        [
            xml_wrap("INVESTIGATION_REQUEST", device_name),
            xml_wrap("AVAILABLE_PLANS", available_skills),
            xml_wrap("INVESTIGATION_CONTEXT", planning_context),
        ]
    )
    log_prompt(
        node_name="planner",
        system_prompt=system_prompt,
        human_message=human_message,
        device_name=device_name,
    )

    response = execute_plan_selection(
        model,
        device_name,
        available_skills,
        planning_context,
        system_prompt,
    )

    device_plan = process_device_plan_response(
        response_content=response,
        model=fast_model,
        device_name=device_name,
    )

    logger.debug("📋 DevicePlan for %s: %s", device_name, device_plan)
    return device_plan
