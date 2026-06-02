"""Planning logic for the planner node."""

from dataclasses import dataclass
from typing import Optional
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langchain_core.language_models import BaseChatModel

from src.util.skills import load_skills
from src.util.skill_routing import get_skills_for_alert
from src.util.validation import validate_structured_output, validate_planning_response
from src.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DevicePlan:
    """A plan tailored for a single device investigation.

    Using flat string fields (no nested objects or lists) keeps this schema
    compatible with all LLM providers when used with structured output.
    """

    device_name: str
    objective: str = ""
    working_plan_steps: str = ""


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


def process_device_plan_response(
    response_content: BaseMessage, model: BaseChatModel, device_name: str
) -> DevicePlan:
    """Process LLM response and extract a single device plan."""
    logger.debug("🧠 Getting structured output for device: %s", device_name)

    result, violations = validate_structured_output(
        raw_text=response_content.content,
        schema=DevicePlan,
        model=model,
        validators=[validate_planning_response],
    )

    logger.debug("📋 Structured output captured: %s", result)

    if violations:
        logger.warning("⚠️ Planning response validation violations: %s", violations)

    if isinstance(result, DevicePlan):
        return result
    elif isinstance(result, dict):
        return DevicePlan(
            device_name=result.get("device_name", device_name),
            objective=result.get("objective", ""),
            working_plan_steps=result.get("working_plan_steps", ""),
        )

    logger.error("❌ Unexpected response format: %s", type(result))
    return DevicePlan(device_name=device_name)
