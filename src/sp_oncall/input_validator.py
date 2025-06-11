import asyncio
from typing import TypedDict
from langchain_core.messages import HumanMessage

from sp_oncall.state import GraphState
from sp_oncall.mcp_node import mcp_node
from sp_oncall.prompts import DEVICE_EXTRACTION_PROMPT
from sp_oncall.utils import load_chat_model
from sp_oncall.configuration import Configuration


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
    user_query = state["user_query"]
    device_name = ""
    max_retries = 3
    tool_limitations_report = []
    assessor_notes_for_final_report = ""

    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)

    try:
        mcp_response = asyncio.run(
            mcp_node(
                messages=HumanMessage(content=user_query),
                system_prompt=DEVICE_EXTRACTION_PROMPT.format(
                    user_query=state["user_query"]
                ),
            )
        )

        response_content = mcp_response.get("messages", "failed")[-1].content

        extraction_result = model.with_structured_output(
            DeviceNameExtractionResponse
        ).invoke(response_content)

        if (
            isinstance(extraction_result, dict)
            and "device_name" in extraction_result
        ):
            device_name = extraction_result["device_name"]
            print(f"Extraction message: {extraction_result["messages"]}")
        else:
            raise ValueError(
                f"Expected DeviceNameExtractionResponse but got {type(extraction_result)}"
            )
    except Exception:
        device_name = None

    if not device_name:
        max_retries = 0
        tool_limitations_report = ["Device extraction failed."]
        assessor_notes_for_final_report = (
            "Device extraction failed prior to planning."
        )

    result_state = {
        "user_query": user_query,
        "device_name": device_name or "",
        "objective": "",
        "working_plan_steps": [],
        "execution_results": [],
        "tool_limitations_report": tool_limitations_report,
        "max_retries": max_retries,
        "current_retries": 0,
        "objective_achieved_assessment": None,
        "assessor_notes_for_final_report": assessor_notes_for_final_report,
        "summary": None,
    }

    return result_state
