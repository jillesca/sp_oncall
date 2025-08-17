import json
from typing import Dict, Any
from dataclasses import replace
from langchain_core.messages import SystemMessage

from schemas import GraphState
from util.llm import load_chat_model
from util.utils import serialize_for_prompt
from configuration import Configuration
from prompts.report_generator import REPORT_GENERATOR_PROMPT_TEMPLATE

# Add logging
from src.logging import get_logger, log_node_execution

logger = get_logger(__name__)


@log_node_execution("Report Generator")
def generate_llm_report_node(state: GraphState) -> GraphState:
    """
    Generate a comprehensive summary report using an LLM.

    This function orchestrates the report generation workflow by:
    1. Preparing report input data from the current state
    2. Setting up the LLM model for report generation
    3. Generating the summary using the LLM
    4. Processing and validating the generated summary
    5. Updating the state with the final report

    Args:
        state: The current GraphState containing all necessary information.

    Returns:
        An updated GraphState with the 'summary' field populated by the LLM.
    """
    logger.info("📄 Generating final summary report")

    try:
        prompt_input = _prepare_report_input(state)
        model = _setup_report_generation_model()
        llm_summary = _generate_llm_summary(model, prompt_input)

        _log_successful_report_generation(llm_summary)
        return _build_report_state(state, llm_summary)

    except Exception as e:
        logger.error("❌ Report generation failed: %s", e)
        error_summary = f"Error generating LLM summary. Details: {e}"
        return _build_report_state(state, error_summary)


def _prepare_report_input(state: GraphState) -> Dict[str, str]:
    """
    Extract and prepare data from the state for the report generator.

    Args:
        state: The current graph state

    Returns:
        Dictionary with formatted input for the prompt template
    """
    logger.debug("📋 Preparing report input data")

    context = {
        "user_query": state.user_query or "N/A",
        "device_name": state.device_name or "N/A",
        "objective": state.objective or "N/A",
        "working_plan_steps": serialize_for_prompt(state.working_plan_steps),
        "execution_results": serialize_for_prompt(state.execution_results),
        "assessor_notes_for_final_report": state.assessor_notes_for_final_report
        or "None",
    }

    logger.debug(
        "📤 Report input prepared for device: %s", context["device_name"]
    )
    return context


def _setup_report_generation_model():
    """Setup and return the LLM model for report generation."""
    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)
    logger.debug(
        "🤖 Using model for report generation: %s", configuration.model
    )
    return model


def _generate_llm_summary(model, prompt_input: Dict[str, str]) -> str:
    """
    Generate a summary using the LLM based on provided input.

    Args:
        model: LLM model for report generation
        prompt_input: Dictionary with formatted data for the prompt

    Returns:
        Generated summary string

    Raises:
        Exception: If report generation fails
    """
    logger.debug("🚀 Generating report from LLM")

    system_message = REPORT_GENERATOR_PROMPT_TEMPLATE.format(**prompt_input)
    response = model.invoke([SystemMessage(content=system_message)])

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


def _log_successful_report_generation(summary: str) -> None:
    """Log successful report generation details."""
    logger.info(
        "✅ Report generation complete, length: %s characters", len(summary)
    )
    logger.debug("📊 Generated report length: %s characters", len(summary))


def _build_report_state(state: GraphState, summary: str) -> GraphState:
    """
    Build the final state with the generated report.

    Args:
        state: Current GraphState
        summary: Generated summary report

    Returns:
        Updated GraphState with summary
    """
    logger.debug("🏗️ Building final report state")

    return replace(state, summary=summary)
