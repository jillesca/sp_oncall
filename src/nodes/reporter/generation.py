"""Report generation functionality."""

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models import BaseChatModel

from src.util.prompt_loader import load_prompt
from src.util.prompt_logger import log_prompt
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

    system_prompt = load_prompt("report_generator")

    log_prompt(
        node_name="report_generator",
        system_prompt=system_prompt,
        human_message=report_context,
    )

    messages = [
        SystemMessage(content=system_prompt),
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
