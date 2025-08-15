import json
from typing import Dict, Any
from langchain_core.messages import SystemMessage

from schemas import GraphState
from util.llm import load_chat_model
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

    updated_state = state.copy()  # type: ignore
    updated_state["summary"] = llm_summary
    return updated_state  # type: ignore


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
        "user_query": state.get("user_query", "N/A"),
        "device_name": state.get("device_name", "N/A"),
        "objective": state.get("objective", "N/A"),
        "working_plan_steps": _serialize_for_prompt(
            state.get("working_plan_steps", [])
        ),
        "execution_results": _serialize_for_prompt(
            state.get("execution_results", [])
        ),
        "assessor_notes_for_final_report": state.get(
            "assessor_notes_for_final_report", "None"
        ),
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

        return (
            response.content if hasattr(response, "content") else str(response)
        )
    except Exception as e:
        return f"Error generating LLM summary. Details: {e}"


def _serialize_for_prompt(value: Any) -> str:
    """Serializes a value for use in a prompt."""
    if isinstance(value, (list, dict)):
        return json.dumps(value, indent=2)
    return value
