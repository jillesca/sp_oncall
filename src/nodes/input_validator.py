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

    This function orchestrates the device extraction workflow by:
    1. Logging the incoming user query
    2. Setting up the LLM model for extraction
    3. Extracting device name via MCP agent
    4. Processing and validating the extracted device name
    5. Building the initial workflow state

    Args:
        state: The current GraphState from the workflow (should contain 'user_query')

    Returns:
        Updated GraphState with device name and initial configuration
    """
    user_query = state.user_query
    logger.info(
        "🔍 Validating input and extracting device name from: %s", user_query
    )

    try:
        model = _setup_extraction_model()
        mcp_response = _execute_device_extraction(user_query)
        response_content = _extract_mcp_response_content(mcp_response)
        device_name = _process_device_extraction_response(
            response_content, model
        )

        _log_successful_extraction(device_name)
        return _build_successful_state(state, device_name)

    except Exception as e:
        logger.error("❌ Device extraction failed: %s", e)
        return _build_failed_state(state)


def _setup_extraction_model():
    """Setup and return the LLM model for device name extraction."""
    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)
    logger.debug("🤖 Using model: %s", configuration.model)
    return model


def _execute_device_extraction(user_query: str) -> dict:
    """
    Execute device extraction via MCP agent.

    Args:
        user_query: The user's input query

    Returns:
        MCP agent response dictionary
    """
    logger.debug("📤 Calling MCP node for device discovery")

    mcp_response = asyncio.run(
        mcp_node(
            messages=HumanMessage(content=user_query),
            system_prompt=DEVICE_EXTRACTION_PROMPT.format(
                user_query=user_query
            ),
        )
    )

    logger.debug("📨 MCP response received for device extraction")
    return mcp_response


def _extract_mcp_response_content(mcp_response: dict) -> str:
    """
    Extract response content from MCP agent response.

    Args:
        mcp_response: Response from MCP agent

    Returns:
        Extracted response content as string

    Raises:
        ValueError: If no valid response content found
    """
    messages = mcp_response.get("messages", [])

    if messages and hasattr(messages[-1], "content"):
        response_content = messages[-1].content
        logger.debug(
            "📨 MCP response content length: %s", len(str(response_content))
        )
        return response_content
    else:
        raise ValueError("No valid response content found in MCP response")


def _process_device_extraction_response(response_content: str, model) -> str:
    """
    Process MCP response and extract device name using LLM.

    Args:
        response_content: Raw response content from MCP agent
        model: LLM model for structured output extraction

    Returns:
        Extracted device name

    Raises:
        ValueError: If no device name found in extraction result
    """
    logger.debug("🔍 Extracting device name from LLM response")

    extraction_result = model.with_structured_output(
        schema=DeviceNameExtractionResponse
    ).invoke(input=response_content)

    device_name, messages = _extract_device_name_response(extraction_result)

    if not device_name:
        raise ValueError(
            f"No device_name found in extraction result: {type(extraction_result)}"
        )

    return device_name


def _log_successful_extraction(device_name: str) -> None:
    """Log successful device name extraction."""
    logger.info("✅ Device name extracted successfully: %s", device_name)


def _build_successful_state(state: GraphState, device_name: str) -> GraphState:
    """
    Build GraphState for successful device extraction.

    Args:
        state: Current GraphState
        device_name: Successfully extracted device name

    Returns:
        Updated GraphState with device name and default configuration
    """
    logger.debug("🏗️ Building successful state with device: %s", device_name)

    return replace(
        state,
        device_name=device_name,
        objective="",
        working_plan_steps=[],
        execution_results=[],
        max_retries=3,
        current_retries=0,
        objective_achieved_assessment=None,
        assessor_feedback_for_retry=None,
        assessor_notes_for_final_report="",
        summary=None,
    )


def _build_failed_state(state: GraphState) -> GraphState:
    """
    Build GraphState for failed device extraction.

    Args:
        state: Current GraphState

    Returns:
        Updated GraphState with empty device name and limited retries
    """
    logger.warning("🚨 No device name found, workflow will be limited")

    return replace(
        state,
        device_name="",
        objective="",
        working_plan_steps=[],
        execution_results=[],
        max_retries=0,
        current_retries=0,
        objective_achieved_assessment=None,
        assessor_feedback_for_retry=None,
        assessor_notes_for_final_report="Device extraction failed prior to planning.",
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
