"""
Core assessment logic for objective evaluation.

This module handles executing the assessment using the LLM and processing
the assessment response to determine workflow completion.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models import BaseChatModel

from schemas import AssessmentOutput
from src.logging import get_logger

logger = get_logger(__name__)


def execute_assessment(
    model: BaseChatModel, assessment_context: str, system_prompt: str
) -> AssessmentOutput:
    """
    Execute objective assessment using the LLM.

    Args:
        model: LLM model for structured output
        assessment_context: Prepared assessment context
        system_prompt: System prompt for assessment

    Returns:
        Assessment output from the LLM
    """
    logger.debug("🚀 Invoking LLM for objective assessment")

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=assessment_context),
    ]

    ai_response = model.with_structured_output(schema=AssessmentOutput).invoke(
        input=messages
    )

    logger.debug("📋 Structured output captured: %s", ai_response)

    assessment = ensure_proper_assessment_format(ai_response)

    logger.debug(
        "📨 Assessment completed: is_objective_achieved=%s",
        assessment.is_objective_achieved,
    )
    return assessment


def ensure_proper_assessment_format(ai_response) -> AssessmentOutput:
    """
    Ensures the AI's response is in a reliable format we can work with.

    Args:
        ai_response: Raw response from the LLM

    Returns:
        Properly formatted AssessmentOutput
    """
    if isinstance(ai_response, AssessmentOutput):
        return ai_response

    if isinstance(ai_response, dict):
        return AssessmentOutput(
            is_objective_achieved=ai_response.get(
                "is_objective_achieved", False
            ),
            notes_for_final_report=ai_response.get(
                "notes_for_final_report",
                "Assessment incomplete. AI response could not be properly interpreted.",
            ),
            feedback_for_retry=ai_response.get("feedback_for_retry"),
        )

    # Handle completely unexpected response types
    return AssessmentOutput(
        is_objective_achieved=False,
        notes_for_final_report=f"Assessment failed. AI returned unexpected response type: {type(ai_response)}",
        feedback_for_retry="Unable to assess due to unexpected AI response format. Please try again.",
    )
