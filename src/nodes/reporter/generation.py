"""Report generation functionality."""

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models import BaseChatModel

from prompts.report_generator import REPORT_GENERATOR_PROMPT
from src.logging import get_logger

logger = get_logger(__name__)


def generate_report(model: BaseChatModel, report_context: str) -> str:
    """
    Generate the final investigation report using the LLM.

    Args:
        model: LLM model for report generation
        report_context: Prepared report context

    Returns:
        Generated report string
    """
    logger.debug("🚀 Generating final report from LLM")

    messages = [
        SystemMessage(content=REPORT_GENERATOR_PROMPT),
        HumanMessage(content=report_context),
    ]

    response = model.invoke(messages)

    return _extract_report_content(response)


def _extract_report_content(response) -> str:
    """
    Extract content from LLM response, handling various response formats.

    Args:
        response: LLM response object

    Returns:
        Extracted content as string
    """
    if hasattr(response, "content"):
        content = response.content

        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            return " ".join(str(item) for item in content)
        else:
            return str(content)
    else:
        return str(response)
