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
    Input Validator node for device extraction.

    This function orchestrates the device extraction workflow by:
    1. Setting up the LLM model for extraction
    2. Extracting device name/information via MCP agent
    3. Processing the response to identify the target device
    4. Building the final state with device information

    Args:
        state: The current GraphState from the workflow (should contain 'user_query')

    Returns:
        Updated GraphState with device_name and objective, or error state
    """
    user_query = state.user_query

    try:
        logger.info("🔍 Starting device extraction workflow")
        model = _setup_extraction_model()
        mcp_response = _execute_device_extraction(user_query)
        response_content = _extract_mcp_response_content(mcp_response)
        device_name = _process_device_extraction_response(response_content, model)

        if device_name:
            _log_successful_extraction(device_name)
            return _build_successful_state(state, device_name)
        else:
            logger.error("❌ Device extraction failed: No device name found")
            return _build_failed_state(state)

    except Exception as e:
        logger.error(f"❌ Device extraction failed with error: {e}")
        return _build_failed_state(state)


def _setup_extraction_model():
    """Set up the language model for device name extraction."""
    logger.debug("⚙️ Setting up extraction model")
    return load_chat_model(Configuration())


def _execute_device_extraction(user_query: str) -> dict:
    """
    Execute device extraction via MCP agent.

    Args:
        user_query: The user's query that needs device extraction

    Returns:
        MCP response containing device extraction results
    """
    logger.debug("🔗 Executing device extraction via MCP agent")

    return asyncio.run(
        mcp_node(
            tool_name="extract_device_name_from_query",
            arguments={"query": user_query},
            system_prompt=DEVICE_EXTRACTION_PROMPT.format(user_query=user_query),
        )
    )


def _extract_mcp_response_content(mcp_response: dict) -> str:
    """
    Extract content from MCP response for device name processing.

    Args:
        mcp_response: Raw response from MCP agent

    Returns:
        Extracted content string for further processing

    Raises:
        ValueError: If response format is invalid
    """
    logger.debug("📋 Extracting content from MCP response")

    if "content" not in mcp_response:
        logger.error("❌ Invalid MCP response: missing 'content' key")
        raise ValueError("Invalid MCP response format")

    content = mcp_response["content"]
    logger.debug(f"📝 Extracted content length: {len(content)} characters")

    return content


def _process_device_extraction_response(response_content: str, model) -> str:
    """
    Process the device extraction response to get device name.

    Args:
        response_content: Content from MCP agent response
        model: LLM model for processing the response

    Returns:
        Extracted device name or empty string if extraction failed
    """
    logger.debug("🧠 Processing device extraction response with LLM")

    try:
        # Use the model to process the response and extract device name
        prompt = f"Extract the device name from this response: {response_content}"
        response = model.invoke([HumanMessage(content=prompt)])

        # Handle different response types
        device_name, _ = _extract_device_name_response(response)

        logger.debug(f"🎯 Extracted device name: '{device_name}'")
        return device_name

    except Exception as e:
        logger.error(f"❌ LLM processing failed: {e}")
        return ""


def _log_successful_extraction(device_name: str) -> None:
    """Log successful device extraction details."""
    logger.info(f"✅ Device extraction successful: '{device_name}'")


def _build_successful_state(state: GraphState, device_name: str) -> GraphState:
    """
    Build the successful state after device extraction.

    Args:
        state: Current GraphState
        device_name: Successfully extracted device name

    Returns:
        Updated GraphState with device information
    """
    logger.debug("🏗️ Building successful extraction state")

    # For now, we'll need to adapt this to work with the new Investigation-based state
    # This is where the actual refactoring needs to happen based on the new state schema
    
    # TODO: Update this to create Investigation objects instead of setting device_name directly
    # The existing logic needs to be refactored to work with the new GraphState schema
    
    return replace(
        state,
        # This needs to be updated to work with investigations list
        # For now, keeping the basic structure
    )


def _build_failed_state(state: GraphState) -> GraphState:
    """
    Build the failed state when device extraction fails.

    Args:
        state: Current GraphState

    Returns:
        GraphState indicating extraction failure
    """
    logger.debug("🚨 Building failed extraction state")

    # TODO: Update this to work with the new Investigation-based state
    # Set appropriate error state in the new schema
    
    return replace(
        state,
        # This needs to be updated to work with investigations list
        # For now, keeping the basic structure
    )


def _extract_device_name_response(extraction_result: Any) -> Tuple[str, str]:
    """
    Extract device name from various response formats.

    Args:
        extraction_result: Response from LLM (could be various types)

    Returns:
        Tuple of (device_name, messages) extracted from the response
    """
    logger.debug("🔍 Extracting device name from response")

    if hasattr(extraction_result, "content"):
        # Standard response format
        content = extraction_result.content
        if isinstance(content, str):
            device_name = content.strip()
            messages = content
        else:
            device_name = str(content).strip()
            messages = str(content)

    elif isinstance(extraction_result, DeviceNameExtractionResponse):
        # Structured response format
        device_name = extraction_result.device_name or ""
        messages = getattr(extraction_result, "messages", "")

    elif isinstance(extraction_result, dict):
        # Dictionary response format
        device_name = extraction_result.get("device_name", "")
        messages = extraction_result.get("messages", "")

    elif isinstance(extraction_result, str):
        # Direct string response
        device_name = extraction_result.strip()
        messages = extraction_result

    else:
        # Unknown response type
        device_name = ""
        messages = ""

    return device_name, messages
