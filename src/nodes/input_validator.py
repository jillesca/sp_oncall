import asyncio
from dataclasses import replace
from typing import Any, Tuple
from langchain_core.messages import HumanMessage

from schemas import GraphState
from schemas.device_extraction_schema import DeviceNameExtractionResponse
from mcp_client import mcp_node
from util.llm import load_chat_model
from configuration import Configuration
from prompts.device_extraction import DEVICE_EXTRACTION_PROMPT

# Add logging
from src.logging import get_logger, log_node_execution

logger = get_logger(__name__)


@log_node_execution("Input Validator")
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
    logger.info(
        f"🔍 Validating input and extracting device name from: {user_query}"
    )

    device_name = ""
    max_retries = 3
    assessor_notes_for_final_report = ""

    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)
    logger.debug("Using model: %s", configuration.model)

    try:
        logger.debug("Calling MCP node for device discovery")
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
            logger.debug(
                "MCP response content length: %s", len(str(response_content))
            )
        else:
            raise ValueError("No valid response content found")

        logger.debug("Extracting device name from LLM response")
        extraction_result = model.with_structured_output(
            schema=DeviceNameExtractionResponse
        ).invoke(input=response_content)

        # Extract device name and messages using pure function
        device_name, messages = _extract_device_name_response(
            extraction_result
        )

        if not device_name:
            raise ValueError(
                f"No device_name found in extraction result: {type(extraction_result)}"
            )

        logger.info("✅ Device name extracted successfully: %s", device_name)

    except Exception as e:
        logger.error("❌ Device extraction failed: %s", e)
        device_name = ""

    if not device_name:
        logger.warning("🚨 No device name found, workflow will be limited")
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


def _extract_device_name_response(extraction_result: Any) -> Tuple[str, str]:
    """
    Extract device name and messages from various LLM response formats.

    This pure function handles different response types that might be returned
    from the LLM during device name extraction, normalizing them into a consistent format.

    Args:
        extraction_result: The response from the LLM, which can be:
                          - DeviceNameExtractionResponse dataclass
                          - Object with device_name and messages attributes
                          - Dictionary with device_name and messages keys
                          - Any other type (fallback)

    Returns:
        Tuple containing:
        - device_name (str): The extracted device name or empty string
        - messages (str): The extraction messages or empty string
    """
    if isinstance(extraction_result, DeviceNameExtractionResponse):
        # Direct dataclass response
        device_name = extraction_result.device_name or ""
        messages = extraction_result.messages or ""
    elif hasattr(extraction_result, "device_name") and hasattr(
        extraction_result, "messages"
    ):
        # Structured object with attributes
        device_name = getattr(extraction_result, "device_name", "")
        messages = getattr(extraction_result, "messages", "")
    elif isinstance(extraction_result, dict):
        # Fallback for dict-style responses
        device_name = extraction_result.get("device_name", "")
        messages = extraction_result.get("messages", "")
    else:
        # Unknown response type
        device_name = ""
        messages = ""

    return device_name, messages
