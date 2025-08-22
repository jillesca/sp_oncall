"""Planning logic for the planner node."""

from dataclasses import dataclass
from typing import List, Optional
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langchain_core.language_models import BaseChatModel

from util.plans import load_plans, plans_to_string
from src.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DevicePlan:
    device_name: str
    role: str = ""
    objective: Optional[str] = None
    working_plan_steps: str = ""


@dataclass
class PlanningResponse:
    plan: List[DevicePlan]

    def __len__(self) -> int:
        return len(self.plan)

    def __iter__(self):
        return iter(self.plan)


def load_available_plans() -> str:
    """Load available plans from the plan repository and format them as string."""
    plans = load_plans()
    available_plans_string = plans_to_string(plans)
    logger.debug("📚 Loaded %s available plans", len(plans))
    return available_plans_string


def execute_plan_selection(
    model: BaseChatModel,
    user_query: str,
    available_plans: str,
    investigations_summary: str,
    system_prompt: str,
) -> BaseMessage:
    """Execute plan selection using the LLM."""
    logger.debug("🚀 Invoking LLM for plan selection")

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"request: {user_query}"),
        HumanMessage(content=f"#available_plans:\n{available_plans}"),
        HumanMessage(content=f"#investigations:\n{investigations_summary}"),
    ]
    response = model.invoke(input=messages)

    logger.debug("📨 LLM plan selection response received")
    return response


def process_planning_response(
    response_content: BaseMessage, model: BaseChatModel
) -> PlanningResponse:
    """Process LLM response and extract planning information."""
    logger.debug("🧠 Getting structured output")

    try:
        response = model.with_structured_output(
            schema=PlanningResponse
        ).invoke(input=response_content.content)

        logger.debug("📋 Structured output captured: %s", response)

        if isinstance(response, PlanningResponse):
            return response
        elif isinstance(response, dict) and "plan" in response:
            return _create_planning_response_from_dict(response)
        else:
            logger.error("❌ Unexpected response format: %s", type(response))
            return PlanningResponse(plan=[])

    except Exception as e:
        logger.error("❌ LLM processing failed: %s", e)
        return PlanningResponse(plan=[])


def _create_planning_response_from_dict(response: dict) -> PlanningResponse:
    """Create PlanningResponse from dictionary."""
    investigations_data = response["plan"]
    plan = [
        (
            DevicePlan(
                device_name=item["device_name"],
                objective=item["objective"],
                working_plan_steps=item["working_plan_steps"],
            )
            if isinstance(item, dict)
            else item
        )
        for item in investigations_data
    ]
    return PlanningResponse(plan=plan)
