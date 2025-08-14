from langchain_core.messages import SystemMessage

from sp_oncall.prompts import PLANNER_PROMPT
from sp_oncall.util.llm import load_chat_model
from sp_oncall.util.plans import load_plan_data
from sp_oncall.configuration import Configuration
from sp_oncall.schemas import GraphState, PlannerOutput


def planner_node(state: GraphState) -> GraphState:
    """ """
    user_query = state["user_query"]
    objective = ""

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
        objective = (
            response.get("objective", "No objective defined in plan."),
        )
        working_plan_steps = response.get("steps", [])

    except Exception as e:
        objective = (
            f"Tool Error: Error extracting device name from user query: {e}",
        )

    result_state = {
        "objective": objective,
        "working_plan_steps": working_plan_steps,
    }
    return result_state
