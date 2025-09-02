"""
Core functionality for the Planner Node.

This module contains the main entry point for the planning workflow that loads plans,
selects appropriate plans, and updates investigations with planning results.
"""

from schemas.state import GraphState
from src.logging import get_logger, log_node_execution
from nodes.common import load_model
from prompts.planner import PLANNER_PROMPT

from .planning import (
    load_available_plans,
    execute_plan_selection,
    process_planning_response,
)
from .context import build_planning_context
from .state import build_successful_planning_state, build_failed_planning_state

logger = get_logger(__name__)


@log_node_execution("Planner")
def planner_node(state: GraphState) -> GraphState:
    """
    Planner node that orchestrates the planning workflow.

    This function orchestrates the planning workflow by:
    1. Loading available plans from the plan repository
    2. Setting up the LLM model for plan selection
    3. Generating a selection prompt with available plans
    4. Processing the LLM response to extract objective and steps
    5. Building the updated state with planning results

    Args:
        state: The current GraphState from the workflow

    Returns:
        Updated GraphState with plan details and selected plan steps
    """
    user_query = state.current_user_request
    logger.info("📋 Planning for user query: %s", user_query)

    try:
        available_plans = load_available_plans()
        model = load_model()
        planning_context = build_planning_context(state)
        response = execute_plan_selection(
            model,
            user_query,
            available_plans,
            planning_context,
            PLANNER_PROMPT,
        )
        planning_response = process_planning_response(
            response_content=response, model=model
        )

        logger.debug("📋 PlanningResponse: %s", planning_response)

        return build_successful_planning_state(state, planning_response)

    except Exception as e:
        logger.error("❌ Plan generation failed: %s", e)
        return build_failed_planning_state(state, e)
