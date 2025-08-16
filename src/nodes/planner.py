from dataclasses import replace
from typing import Any, Tuple, List
from langchain_core.messages import SystemMessage

from util.llm import load_chat_model
from util.plans import load_plan_data
from configuration import Configuration
from prompts.planner import PLANNER_PROMPT
from schemas import GraphState, PlannerOutput

# Add logging
from src.logging import get_logger, log_node_execution

logger = get_logger(__name__)


@log_node_execution("Planner")
def planner_node(state: GraphState) -> GraphState:
    """
    Planner node.

    Uses LLM to dynamically select the plan based on user query. Loads the
    selected plan and populates the GraphState.

    Args:
        state: The current GraphState from the workflow

    Returns:
        Updated GraphState with plan details and selected plan steps
    """
    user_query = state.user_query
    logger.info("📋 Planning for user query: %s", user_query)

    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)
    logger.debug("Using model: %s", configuration.model)

    available_plans = load_plan_data()
    logger.debug("Loaded %s available plans", len(available_plans))

    try:
        logger.debug("Generating plan selection prompt")
        system_message = PLANNER_PROMPT.format(
            user_query=user_query, available_plans=available_plans
        )

        logger.debug("Invoking LLM for plan selection")
        response = model.with_structured_output(schema=PlannerOutput).invoke(
            input=[
                SystemMessage(content=system_message),
            ]
        )

        objective, working_plan_steps = _extract_planner_response(response)
        logger.info(
            "✅ Plan generation successful - Selected plan with %s steps",
            len(working_plan_steps),
        )
        logger.debug("Objective: %s", objective)

    except Exception as e:
        logger.error("❌ Plan generation failed: %s", e)
        objective = (
            f"Tool Error: Error extracting device name from user query: {e}"
        )
        working_plan_steps = []

    return replace(
        state, objective=objective, working_plan_steps=working_plan_steps
    )


def _extract_planner_response(response: Any) -> Tuple[str, List[Any]]:
    """
    Extract objective and steps from various LLM response formats.

    This pure function handles different response types that might be returned
    from the LLM, normalizing them into a consistent format.

    Args:
        response: The response from the LLM, which can be:
                 - PlannerOutput dataclass
                 - Object with objective and steps attributes
                 - Dictionary with objective and steps keys
                 - Any other type (fallback)

    Returns:
        Tuple containing:
        - objective (str): The extracted objective or default message
        - working_plan_steps (List[Any]): The extracted steps or empty list
    """
    default_objective = "No objective defined in plan."

    if isinstance(response, PlannerOutput):
        # Direct dataclass response
        objective = response.objective or default_objective
        working_plan_steps = response.steps or []
    elif hasattr(response, "objective") and hasattr(response, "steps"):
        # Structured object with attributes
        objective = getattr(response, "objective", default_objective)
        working_plan_steps = getattr(response, "steps", [])
    elif isinstance(response, dict):
        # Fallback for dict-style responses
        objective = response.get("objective", default_objective)
        working_plan_steps = response.get("steps", [])
    else:
        # Unknown response type
        objective = default_objective
        working_plan_steps = []

    return objective, working_plan_steps
