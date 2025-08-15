import asyncio
from typing import TypedDict
from dataclasses import replace
from langchain_core.messages import HumanMessage

from schemas import GraphState
from mcp_client import mcp_node
from util.llm import load_chat_model
from configuration import Configuration
from prompts.device_extraction import DEVICE_EXTRACTION_PROMPT


class DeviceNameExtractionResponse(TypedDict):
    device_name: str
    messages: str


def input_validator_node(state: GraphState) -> GraphState:
    """
    Input Validator & Planner node.

    Extracts device_name from user_query using gNMIBuddy.get_devices() and LLM.
    Parses user_query for intent to dynamically select a plan.
    Loads the selected plan and populates the initial GraphState.

    Args:
        state: The current GraphState from the workflow (should contain 'user_query')

    Returns:
        Updated GraphState with plan details and validation
    """
    user_query = state.user_query
    device_name = ""
    max_retries = 3
    assessor_notes_for_final_report = ""

    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)

    try:
        mcp_response = asyncio.run(
            mcp_node(
                messages=HumanMessage(content=user_query),
                system_prompt=DEVICE_EXTRACTION_PROMPT.format(
                    user_query=state.user_query
                ),
            )
        )

        # Handle the response properly - messages should be a list
        messages = mcp_response.get("messages", [])
        if messages and hasattr(messages[-1], "content"):
            response_content = messages[-1].content
        else:
            raise ValueError("No valid response content found")

        extraction_result = model.with_structured_output(
            DeviceNameExtractionResponse
        ).invoke(response_content)

        # Handle structured output properly - it could be a BaseModel or dict
        if isinstance(extraction_result, dict):
            device_name = extraction_result.get("device_name", "")
            print(
                f"Extraction message: {extraction_result.get('messages', '')}"
            )
        else:
            # Assume it's a structured object with attributes
            device_name = getattr(extraction_result, "device_name", "")
            messages_attr = getattr(extraction_result, "messages", "")
            print(f"Extraction message: {messages_attr}")

        if not device_name:
            raise ValueError(
                f"No device_name found in extraction result: {type(extraction_result)}"
            )
    except Exception:
        device_name = ""

    if not device_name:
        max_retries = 0
        assessor_notes_for_final_report = (
            "Device extraction failed prior to planning."
        )

    return replace(
        state,
        device_name=device_name,
        objective="",
        working_plan_steps=[],
        execution_results=[],
        max_retries=max_retries,
        current_retries=0,
        objective_achieved_assessment=None,
        assessor_feedback_for_retry=None,
        assessor_notes_for_final_report=assessor_notes_for_final_report,
        summary=None,
    )
