"""State management for planner workflow."""

from dataclasses import replace
from schemas.state import GraphState
from .planning import PlanningResponse
from src.logging import get_logger

logger = get_logger(__name__)


def build_successful_planning_state(
    state: GraphState, planning_response: PlanningResponse
) -> GraphState:
    """
    Build GraphState for successful planning.

    Args:
        state: Current GraphState
        planning_response: PlanningResponse containing device-specific plans

    Returns:
        Updated GraphState with planning results applied to matching investigations
    """
    logger.debug("🏗️ Building successful planning state")

    # Create a mapping of device plans for efficient lookup
    device_plans_map = {
        plan.device_name: plan for plan in planning_response.plan
    }

    # Update investigations with planning data
    updated_investigations = []
    for investigation in state.investigations:
        device_plan = device_plans_map.get(investigation.device_name)
        if device_plan:
            # Update investigation with planning data using replace
            updated_investigation = replace(
                investigation,
                objective=device_plan.objective,
                working_plan_steps=device_plan.working_plan_steps,
            )
            updated_investigations.append(updated_investigation)
            logger.debug(
                "📝 Updated investigation for device: %s",
                investigation.device_name,
            )
        else:
            # Keep investigation unchanged if no plan found
            updated_investigations.append(investigation)
            logger.debug(
                "⚠️ No plan found for device: %s", investigation.device_name
            )

    return replace(state, investigations=updated_investigations)


def build_failed_planning_state(
    state: GraphState, error: Exception
) -> GraphState:
    """
    Build GraphState for failed planning.

    Args:
        state: Current GraphState
        error: Exception that occurred during planning

    Returns:
        Updated GraphState with error information applied to investigations
    """
    logger.debug("🏗️ Building failed planning state due to error: %s", error)

    error_objective = (
        f"Planning Error: Failed to generate plan for device - {error}"
    )
    error_working_plan_steps = "Planning failed. Manual intervention required."

    # Update all investigations with error information
    updated_investigations = []
    for investigation in state.investigations:
        updated_investigation = replace(
            investigation,
            objective=error_objective,
            working_plan_steps=error_working_plan_steps,
            error_details=str(error),
        )
        updated_investigations.append(updated_investigation)
        logger.debug(
            "❌ Updated investigation with error for device: %s",
            investigation.device_name,
        )

    return replace(state, investigations=updated_investigations)
