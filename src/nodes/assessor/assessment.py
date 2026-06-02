"""
Core assessment logic for objective evaluation.

The assessor returns a structured VERDICT/REASON response so the executor
has specific feedback when a retry is triggered. The REASON is injected into
the next execution attempt, turning blind retries into targeted corrections.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models import BaseChatModel

from src.logging import get_logger

logger = get_logger(__name__)

_VERDICT_YES = "YES"
_VERDICT_NO = "NO"


def execute_assessment(
    model: BaseChatModel, assessment_context: str, system_prompt: str
) -> tuple[bool, str]:
    """Execute objective assessment using the LLM.

    Asks the LLM to respond with VERDICT: YES/NO and REASON: <explanation>.
    Returns a tuple of (objective_achieved, reason).

    The reason is passed back to the executor on retry so the next attempt
    can address the specific gap rather than repeating the same investigation.

    Args:
        model: LLM model to invoke.
        assessment_context: Prepared assessment context.
        system_prompt: System prompt for assessment.

    Returns:
        Tuple of (True if objective achieved, reason string).
    """
    logger.debug("🚀 Invoking LLM for objective assessment")

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=assessment_context),
    ]

    response = model.invoke(input=messages)
    content = response.content if isinstance(response.content, str) else str(response.content)
    objective_achieved, reason = _parse_assessment_response(content)

    logger.debug(
        "📨 Assessment response: verdict=%s reason=%s",
        _VERDICT_YES if objective_achieved else _VERDICT_NO,
        reason[:200],
    )
    return objective_achieved, reason


def _parse_assessment_response(content: str) -> tuple[bool, str]:
    """Parse the VERDICT/REASON response from the assessor LLM.

    Expected format:
        VERDICT: YES
        REASON: <explanation>

    Falls back gracefully if the model ignores the format and responds
    with a bare YES or NO.
    """
    upper = content.upper()
    reason = _extract_reason(content)

    if "VERDICT:" in upper:
        verdict_line = upper.split("VERDICT:", 1)[1].lstrip()
        objective_achieved = verdict_line.startswith(_VERDICT_YES)
        return objective_achieved, reason

    objective_achieved = _VERDICT_YES in upper
    return objective_achieved, reason


def _extract_reason(content: str) -> str:
    """Extract the REASON value from the assessor response."""
    for line in content.splitlines():
        if line.upper().startswith("REASON:"):
            return line.split(":", 1)[1].strip()
    return ""
