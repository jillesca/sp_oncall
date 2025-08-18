import asyncio
from dataclasses import replace
from typing import Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage


from schemas import GraphState
from schemas.state import (
    Investigation,
    InvestigationStatus,
    InvestigationPriority,
)
from mcp_client import mcp_node
from util.llm import load_chat_model
from configuration import Configuration
from prompts.investigation_planning import INVESTIGATION_PLANNING_PROMPT

from src.logging import (
    get_logger,
    log_node_execution,
)

logger = get_logger(__name__)


@log_node_execution("Input Validator")
def input_validator_node(state: GraphState) -> GraphState:
    """
    Input Validator node for multi-device investigation setup.

    This function orchestrates the multi-device investigation workflow by:
    1. Setting up the LLM model for extraction
    2. Extracting device names/information via MCP agent
    3. Processing the response to identify target devices
    4. Creating Investigation objects for each device
    5. Setting device profiles, priorities, and dependencies
    6. Building the final state with investigations list

    Args:
        state: The current GraphState from the workflow (should contain 'user_query')

    Returns:
        Updated GraphState with investigations list populated, or error state
    """
    user_query = state.user_query

    try:
        logger.info("🔍 Starting multi-device investigation setup")
        model = _setup_planning_model()
        mcp_response = _execute_investigation_planning(user_query)
        response_content = _extract_mcp_response_content(mcp_response)
        device_names = _process_investigation_planning_response(
            response_content, model
        )

        if device_names:
            investigations = _create_investigations_from_devices(
                device_names, user_query
            )
            _log_successful_investigation_planning(investigations)
            return _build_successful_state_with_investigations(
                state, investigations
            )
        else:
            logger.error("❌ Investigation planning failed: No devices found")
            return _build_failed_state(state)

    except Exception as e:
        logger.error(f"❌ Investigation planning failed with error: {e}")
        return _build_failed_state(state)


def _setup_planning_model():
    """Set up the language model for investigation planning."""
    logger.debug("⚙️ Setting up planning model")
    configuration = Configuration.from_context()
    return load_chat_model(configuration.model)


def _execute_investigation_planning(user_query: str) -> dict:
    """
    Execute investigation planning via MCP agent.

    Args:
        user_query: The user's query that needs investigation planning

    Returns:
        MCP response containing investigation planning results
    """
    logger.debug("🔗 Executing investigation planning via MCP agent")

    # Create the message for the MCP agent
    message = HumanMessage(
        content=f"Plan investigation for this query: {user_query}"
    )

    return asyncio.run(
        mcp_node(
            messages=message,
            system_prompt=INVESTIGATION_PLANNING_PROMPT.format(
                user_query=user_query
            ),
        )
    )


def _extract_mcp_response_content(mcp_response: Any) -> Any:
    """
    Extract content from MCP response for device name processing.

    The MCP response contains a 'messages' list with AIMessage and ToolMessage objects.
    We need to get the content from the last AIMessage which contains the final result.

    Args:
        mcp_response: Raw response from MCP agent containing messages list

    Returns:
        Extracted content string from the last AIMessage

    Raises:
        ValueError: If response format is invalid or no AIMessage found
    """
    logger.debug("📋 Extracting content from MCP response")
    logger.debug(
        f"🔍 MCP response keys: {list(mcp_response.keys()) if isinstance(mcp_response, dict) else 'Not a dict'}"
    )

    # Check if the response has the expected structure
    if not isinstance(mcp_response, dict) or "messages" not in mcp_response:
        logger.error("❌ Invalid MCP response: missing 'messages' key")
        raise ValueError("Invalid MCP response format: missing 'messages' key")

    messages = mcp_response["messages"]
    if not isinstance(messages, list) or len(messages) == 0:
        logger.error(
            "❌ Invalid MCP response: 'messages' is not a list or is empty"
        )
        raise ValueError(
            "Invalid MCP response format: 'messages' is not a list or is empty"
        )

    # Find the last AIMessage in the messages list
    last_ai_message = None
    for message in reversed(messages):
        if hasattr(message, "content") and hasattr(message, "__class__"):
            if isinstance(message, AIMessage):
                last_ai_message = message
                break

    if last_ai_message is None:
        logger.error("❌ No AIMessage found in MCP response messages")
        raise ValueError("No AIMessage found in MCP response messages")

    content = last_ai_message.content
    logger.debug(f"🎯 Content: {content}")

    return content


def _process_investigation_planning_response(
    response_content: str, model
) -> List[str]:
    """
    Process the investigation planning response to get multiple device names.

    Args:
        response_content: Content from MCP agent response
        model: LLM model for processing the response

    Returns:
        List of extracted device names or empty list if extraction failed
    """
    logger.debug("🧠 Processing investigation planning response with LLM")

    try:
        # Use the model to process the response and extract device names
        prompt = f"""Extract all device names from this response. Return only the device names, one per line.
        Response to process: {response_content}"""
        response = model.invoke([HumanMessage(content=prompt)])

        # Handle different response types and extract device names
        device_names = _extract_device_names_from_response(response)

        logger.debug(
            f"🎯 Extracted {len(device_names)} device names: {device_names}"
        )
        return device_names

    except Exception as e:
        logger.error(f"❌ LLM processing failed: {e}")
        return []


def _extract_device_names_from_response(extraction_result: Any) -> List[str]:
    """
    Extract device names from various response formats.

    Args:
        extraction_result: Response from LLM (could be various types)

    Returns:
        List of device names extracted from the response
    """
    logger.debug("🔍 Extracting device names from response")

    if hasattr(extraction_result, "content"):
        content = extraction_result.content
    elif isinstance(extraction_result, str):
        content = extraction_result
    else:
        content = str(extraction_result)

    # Parse device names from content (assuming one per line or comma-separated)
    if isinstance(content, str):
        # Split by newlines and clean up
        device_names = [
            name.strip() for name in content.split("\n") if name.strip()
        ]

        # If no newlines, try comma separation
        if len(device_names) == 1 and "," in device_names[0]:
            device_names = [
                name.strip()
                for name in device_names[0].split(",")
                if name.strip()
            ]

        # Filter out empty names and common non-device responses
        device_names = [
            name
            for name in device_names
            if name
            and not name.lower() in ["none", "no device", "not found", "n/a"]
        ]

        return device_names

    return []


def _create_investigations_from_devices(
    device_names: List[str], user_query: str
) -> List[Investigation]:
    """
    Create Investigation objects from a list of device names.

    Args:
        device_names: List of device names extracted from user query
        user_query: Original user query for context

    Returns:
        List of Investigation objects with appropriate priorities and dependencies
    """
    logger.debug(f"🏗️ Creating investigations for {len(device_names)} devices")

    investigations = []

    for i, device_name in enumerate(device_names):
        # Determine device profile based on device name patterns
        device_profile = _determine_device_profile(device_name)

        # Determine priority based on device type and position
        priority = _determine_investigation_priority(
            device_name, device_profile, i
        )

        # Create the investigation
        investigation = Investigation(
            device_name=device_name,
            device_profile=device_profile,
            objective=_extract_device_specific_objective(
                device_name, user_query
            ),
            status=InvestigationStatus.PENDING,
            priority=priority,
            dependencies=_determine_investigation_dependencies(
                device_name, device_names
            ),
            retry_count=0,
        )

        investigations.append(investigation)
        logger.debug(
            f"📋 Created investigation for {device_name} with priority {priority}"
        )

    return investigations


def _determine_device_profile(device_name: str) -> str:
    """
    Determine device profile based on device name patterns.

    Args:
        device_name: Name of the device

    Returns:
        Device profile string (e.g., "router", "switch", "firewall")
    """
    device_name_lower = device_name.lower()

    # Common device type patterns
    if any(
        pattern in device_name_lower
        for pattern in ["rtr", "router", "r-", "gw", "gateway"]
    ):
        return "router"
    elif any(
        pattern in device_name_lower for pattern in ["sw", "switch", "sw-"]
    ):
        return "switch"
    elif any(
        pattern in device_name_lower
        for pattern in ["fw", "firewall", "asa", "pix"]
    ):
        return "firewall"
    elif any(
        pattern in device_name_lower
        for pattern in ["ap", "access", "wireless"]
    ):
        return "access_point"
    elif any(
        pattern in device_name_lower for pattern in ["core", "agg", "dist"]
    ):
        return "core_device"
    else:
        return "network_device"


def _determine_investigation_priority(
    device_name: str, device_profile: str, position: int
) -> InvestigationPriority:
    """
    Determine investigation priority based on device characteristics.

    Args:
        device_name: Name of the device
        device_profile: Device profile/type
        position: Position in the device list (for ordering)

    Returns:
        Investigation priority
    """
    device_name_lower = device_name.lower()

    # High priority for core infrastructure
    if device_profile == "core_device" or any(
        pattern in device_name_lower for pattern in ["core", "main", "primary"]
    ):
        return InvestigationPriority.HIGH

    # High priority for the first device (usually the most relevant)
    if position == 0:
        return InvestigationPriority.HIGH

    # Medium priority for routers and firewalls
    if device_profile in ["router", "firewall"]:
        return InvestigationPriority.MEDIUM

    # Lower priority for edge devices
    return InvestigationPriority.LOW


def _determine_investigation_dependencies(
    device_name: str, all_device_names: List[str]
) -> List[str]:
    """
    Determine which other devices this investigation depends on.

    Args:
        device_name: Current device name
        all_device_names: List of all device names in the investigation

    Returns:
        List of device names this investigation depends on
    """
    dependencies = []
    device_name_lower = device_name.lower()

    # Edge devices typically depend on core devices
    if any(
        pattern in device_name_lower for pattern in ["edge", "access", "leaf"]
    ):
        for other_device in all_device_names:
            if other_device != device_name:
                other_device_lower = other_device.lower()
                if any(
                    pattern in other_device_lower
                    for pattern in ["core", "spine", "agg", "dist"]
                ):
                    dependencies.append(other_device)

    return dependencies


def _extract_device_specific_objective(
    device_name: str, user_query: str
) -> Optional[str]:
    """
    Extract device-specific objective from the user query.

    Args:
        device_name: Name of the device
        user_query: Original user query

    Returns:
        Device-specific objective or None
    """
    # For now, return a simple objective based on the user query
    # This could be enhanced with more sophisticated parsing
    return f"Investigate {device_name} in relation to: {user_query}"


def _log_successful_investigation_planning(
    investigations: List[Investigation],
) -> None:
    """Log successful investigation planning details."""
    logger.info(
        f"✅ Investigation planning successful: {len(investigations)} investigations created"
    )
    for investigation in investigations:
        logger.info(
            f"  📋 {investigation.device_name} ({investigation.priority.value}, {len(investigation.dependencies)} deps)"
        )


def _build_successful_state_with_investigations(
    state: GraphState, investigations: List[Investigation]
) -> GraphState:
    """
    Build the successful state after multi-device extraction.

    Args:
        state: Current GraphState
        investigations: List of Investigation objects created

    Returns:
        Updated GraphState with investigations populated
    """
    logger.debug(
        f"🏗️ Building successful state with {len(investigations)} investigations"
    )

    return replace(state, investigations=investigations)


def _build_failed_state(state: GraphState) -> GraphState:
    """
    Build the failed state when investigation planning fails.

    Args:
        state: Current GraphState

    Returns:
        GraphState indicating planning failure
    """
    logger.debug("🚨 Building failed planning state")

    # Return state with empty investigations list to indicate failure
    return replace(state, investigations=[])
