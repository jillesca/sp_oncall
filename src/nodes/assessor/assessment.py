"""
Core assessment logic for objective evaluation.

Replaces the structured AssessmentOutput approach with a simple YES/NO
verdict from the LLM. The only decision needed is whether the objective
was achieved — structured output overhead is not justified for a boolean.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models import BaseChatModel

from src.logging import get_logger

logger = get_logger(__name__)


def execute_assessment(
    model: BaseChatModel, assessment_context: str, system_prompt: str
) -> bool:
    """Execute objective assessment using the LLM.

    Asks the LLM to respond YES or NO based on whether the phase objective
    was achieved. Returns True when the response contains YES.

    Args:
        model: LLM model to invoke.
        assessment_context: Prepared assessment context.
        system_prompt: System prompt for assessment.

    Returns:
        True if the objective is achieved, False if a retry is warranted.
    """
    logger.debug("🚀 Invoking LLM for objective assessment")

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=assessment_context),
    ]

    response = model.invoke(input=messages)
    objective_achieved = "YES" in response.content.upper()

    logger.debug(
        "📨 Assessment response: %s → achieved=%s",
        response.content[:200],
        objective_achieved,
    )
    return objective_achieved
