"""
Per-device planning logic.

Generates a tailored investigation plan for a single device by loading
relevant skills, invoking the LLM, and parsing the structured response.
Called from the per-device sub-graph rather than the outer graph.
"""

from typing import Optional

from schemas.state import Investigation
from src.logging import get_logger
from nodes.common import load_model, load_fast_model
from src.util.prompt_loader import load_prompt

from .planning import (
    DevicePlan,
    load_available_skills,
    execute_plan_selection,
    process_device_plan_response,
)
from .context import build_planning_context

logger = get_logger(__name__)


def plan_single_device(
    investigation: Investigation,
    event_type: Optional[str] = None,
) -> DevicePlan:
    """Generate an investigation plan for a single device.

    Args:
        investigation: The device investigation to plan for.
        event_type: Alert event type used to filter relevant skills.
                    None for manual queries (loads all skills).

    Returns:
        A DevicePlan with objective and step-by-step instructions for this device.

    Raises:
        Exception: If plan generation fails — callers should handle and mark
                   the investigation as failed.
    """
    logger.info("📋 Planning for device: %s", investigation.device_name)

    available_skills = load_available_skills(event_type)
    model = load_model()
    fast_model = load_fast_model()
    planning_context = build_planning_context(investigation)

    response = execute_plan_selection(
        model,
        investigation.device_name,
        available_skills,
        planning_context,
        load_prompt("planner"),
    )

    device_plan = process_device_plan_response(
        response_content=response,
        model=fast_model,
        device_name=investigation.device_name,
    )

    logger.debug("📋 DevicePlan for %s: %s", investigation.device_name, device_plan)
    return device_plan
