from langchain_core.messages import SystemMessage

from util.llm import load_chat_model
from util.plans import load_plan_data
from configuration import Configuration
from prompts.planner import PLANNER_PROMPT
from schemas import GraphState, PlannerOutput


def planner_node(state: GraphState) -> GraphState:
    """
    Planner node that determines objective and working plan steps.

    Args:
        state: The current GraphState from the workflow

    Returns:
        Updated GraphState with objective and working_plan_steps populated
    """
    # Create a copy of the current state to modify
    updated_state = state.copy()

    user_query = state["user_query"]
    objective = ""
    working_plan_steps = []

    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)

    available_plans = load_plan_data()

    try:
        system_message = PLANNER_PROMPT.format(
            user_query=user_query, available_plans=available_plans
        )
        response = model.with_structured_output(PlannerOutput).invoke(
            [
                SystemMessage(content=system_message),
            ]
        )

        print(response)

        # Handle structured output properly - it could be a BaseModel or dict
        if isinstance(response, dict):
            objective = response.get(
                "objective", "No objective defined in plan."
            )
            working_plan_steps = response.get("steps", [])
        else:
            # Assume it's a structured object with attributes
            objective = getattr(
                response, "objective", "No objective defined in plan."
            )
            working_plan_steps = getattr(response, "steps", [])

    except Exception as e:
        objective = (
            f"Tool Error: Error extracting device name from user query: {e}"
        )
        working_plan_steps = []

    # Update the state with new values
    updated_state["objective"] = objective
    updated_state["working_plan_steps"] = working_plan_steps

    return updated_state
