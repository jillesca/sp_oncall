"""Planning logic for the planner node."""

from dataclasses import dataclass
from typing import List, Optional
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langchain_core.language_models import BaseChatModel

from src.util.skills import load_skills
from src.util.skill_routing import get_skills_for_alert
from src.util.validation import validate_structured_output, validate_planning_response
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


def load_available_skills(event_type: Optional[str] = None) -> str:
    """Load skills filtered by alert event_type, or all skills for manual queries."""
    if event_type:
        skill_names = get_skills_for_alert(event_type)
        logger.debug(
            "📚 Loading %d skills for event_type '%s'",
            len(skill_names),
            event_type,
        )
        return load_skills(skill_names)

    logger.debug("📚 Loading all skills for manual query")
    return load_skills()


def execute_plan_selection(
    model: BaseChatModel,
    user_query: str,
    available_plans: str,
    planning_context: str,
    system_prompt: str,
) -> BaseMessage:
    """Execute plan selection using the LLM with comprehensive context."""
    logger.debug("🚀 Invoking LLM for plan selection")

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"request: {user_query}"),
        HumanMessage(content=f"#available_plans:\n{available_plans}"),
        HumanMessage(content=f"#context:\n{planning_context}"),
    ]
    response = model.invoke(input=messages)

    logger.debug("📨 LLM plan selection response received")
    return response


def process_planning_response(
    response_content: BaseMessage, model: BaseChatModel
) -> PlanningResponse:
    """Process LLM response and extract planning information."""
    logger.debug("🧠 Getting structured output")

    result, violations = validate_structured_output(
        raw_text=response_content.content,
        schema=PlanningResponse,
        model=model,
        validators=[validate_planning_response],
    )

    logger.debug("📋 Structured output captured: %s", result)

    if violations:
        logger.warning("⚠️ Planning response validation violations: %s", violations)

    if isinstance(result, PlanningResponse):
        return result
    elif isinstance(result, dict) and "plan" in result:
        return _create_planning_response_from_dict(result)

    logger.error("❌ Unexpected response format: %s", type(result))
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
