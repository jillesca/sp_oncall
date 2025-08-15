import json
from typing import Dict, Any
from dataclasses import replace
from langchain_core.messages import SystemMessage

from schemas import GraphState
from util.llm import load_chat_model
from util.utils import serialize_for_prompt
from configuration import Configuration
from prompts.report_generator import REPORT_GENERATOR_PROMPT_TEMPLATE


def generate_llm_report_node(state: GraphState) -> GraphState:
    """
    Generate a comprehensive summary report using an LLM.

    Args:
        state: The current GraphState containing all necessary information.

    Returns:
        An updated GraphState with the 'summary' field populated by the LLM.
    """
    prompt_input = prepare_report_input(state)
    llm_summary = generate_llm_summary(prompt_input)

    return replace(state, summary=llm_summary)


def prepare_report_input(state: GraphState) -> Dict[str, str]:
    """
    Extract and prepare data from the state for the report generator.
    Serializes structured data as JSON strings for direct use in the prompt.

    Args:
        state: The current graph state

    Returns:
        Dictionary with formatted input for the prompt template
    """
    # Extract basic data with defaults
    context = {
        "user_query": state.user_query or "N/A",
        "device_name": state.device_name or "N/A",
        "objective": state.objective or "N/A",
        "working_plan_steps": serialize_for_prompt(state.working_plan_steps),
        "execution_results": serialize_for_prompt(state.execution_results),
        "assessor_notes_for_final_report": state.assessor_notes_for_final_report
        or "None",
    }
    return context


def generate_llm_summary(prompt_input: Dict[str, str]) -> str:
    """
    Generate a summary using the LLM based on provided input.

    Args:
        prompt_input: Dictionary with formatted data for the prompt

    Returns:
        Generated summary string
    """
    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)
    try:
        system_message = REPORT_GENERATOR_PROMPT_TEMPLATE.format(
            **prompt_input
        )
        response = model.invoke(
            [
                SystemMessage(content=system_message),
            ]
        )

        if hasattr(response, "content"):
            content = response.content
            # Content might be a string or list, ensure we return a string
            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                # Join list elements if it's a list
                return " ".join(str(item) for item in content)
            else:
                return str(content)
        else:
            return str(response)
    except Exception as e:
        return f"Error generating LLM summary. Details: {e}"
