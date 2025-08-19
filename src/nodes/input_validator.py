import asyncio
from typing import Any, List
from dataclasses import dataclass, replace
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from schemas.state import (
    GraphState,
    Investigation,
)
from src.logging import (
    get_logger,
    log_node_execution,
)
from mcp_client import mcp_node
from util.llm import load_chat_model
from configuration import Configuration
from prompts.investigation_planning import INVESTIGATION_PLANNING_PROMPT

logger = get_logger(__name__)


@dataclass
class DeviceToInvestigate:
    device_name: str
    device_profile: str
    role: str = ""


@dataclass
class InvestigationPlanningResponse:
    devices: List[DeviceToInvestigate]

    def __len__(self) -> int:
        """Return the number of devices."""
        return len(self.devices)

    def __iter__(self):
        """Make InvestigationList iterable."""
        return iter(self.devices)


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
        investigation_list = _process_investigation_planning_response(
            response_content, model=model
        )

        # Happy path: Create Investigation objects and update state
        if not investigation_list or len(investigation_list) == 0:
            logger.warning(
                "⚠️ No devices found in investigation planning response"
            )
            return replace(state, investigations=[])

        investigations = _create_investigations_from_response(
            investigation_list
        )
        _log_successful_investigation_planning(investigation_list)

        return replace(state, investigations=investigations)

    except Exception as e:
        logger.error("❌ Investigation planning failed with error: %s", e)
        return _build_failed_state(state)


def _setup_planning_model():
    """Set up the language model for investigation planning."""
    logger.debug("⚙️ Setting up planning model")
    configuration = Configuration.from_context()
    return load_chat_model(configuration.model)


def _execute_investigation_planning(
    user_query: str, response_format: Any = None
) -> dict:
    """
    Execute investigation planning via MCP agent.

    Args:
        user_query: The user's query that needs investigation planning

    Returns:
        MCP response containing investigation planning results
    """
    logger.debug(
        "🔗 Executing investigation planning via MCP agent. User query: %s",
        user_query,
    )

    message = HumanMessage(content=f"User query: {user_query}")

    return asyncio.run(
        mcp_node(
            message=message,
            system_prompt=INVESTIGATION_PLANNING_PROMPT,
            response_format=response_format,
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
        "🔍 MCP response keys: %s",
        (
            list(mcp_response.keys())
            if isinstance(mcp_response, dict)
            else "Not a dict"
        ),
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

    logger.debug("🎯 Content: %s", last_ai_message.content)

    return last_ai_message


def _process_investigation_planning_response(
    response_content: BaseMessage, model: BaseChatModel
) -> InvestigationPlanningResponse:
    """
    Parses the MCP agent response content for investigation planning.

    Args:
        response_content: Content from MCP agent response
        model: LLM model for processing the response

    Returns:
        List of extracted device names or empty list if extraction failed
    """
    logger.debug("🧠 Getting structured output")

    try:
        # Use the model to process the response and extract device names
        response = model.with_structured_output(
            schema=InvestigationPlanningResponse
        ).invoke(input=response_content.content)

        from src.logging import debug_capture_object

        # Capture any object
        debug_capture_object(
            response, label="_process_investigation_planning_response"
        )

        logger.debug("🎯 Extracted device names: %s", response)

        # Ensure we have a proper InvestigationList object
        if isinstance(response, InvestigationPlanningResponse):
            return response
        elif isinstance(response, dict) and "devices" in response:
            # Handle case where response is a dict with the expected structure
            investigations_data = response["devices"]
            devices = [
                (
                    DeviceToInvestigate(
                        device_name=item["device_name"],
                        device_profile=item["device_profile"],
                        role=item["role"],
                    )
                    if isinstance(item, dict)
                    else item
                )
                for item in investigations_data
            ]
            return InvestigationPlanningResponse(devices=devices)
        else:
            logger.error("❌ Unexpected response format: %s", type(response))
            return InvestigationPlanningResponse(devices=[])

    except Exception as e:
        logger.error("❌ LLM processing failed: %s", e)
        return InvestigationPlanningResponse(devices=[])


def _log_successful_investigation_planning(
    devices: InvestigationPlanningResponse,
) -> None:
    """Log successful investigation planning details."""
    logger.info(
        "✅ Investigation planning successful: %d devices created",
        len(devices),
    )
    for investigation in devices:
        logger.info(
            "  📋 %s (%s)",
            investigation.device_name,
            investigation.device_profile,
        )


def _create_investigations_from_response(
    planning_response: InvestigationPlanningResponse,
) -> List[Investigation]:
    """
    Create Investigation objects from the planning response.

    Args:
        planning_response: The parsed response containing device information

    Returns:
        List of Investigation objects, one for each device
    """
    logger.debug(
        "🏗️ Creating %d Investigation objects from planning response",
        len(planning_response),
    )

    investigations = []
    for device in planning_response:
        investigation = Investigation(
            device_name=device.device_name,
            device_profile=device.device_profile,
        )
        investigations.append(investigation)
        logger.debug(
            "  ✅ Created investigation for device: %s", device.device_name
        )

    return investigations


def _build_failed_state(state: GraphState) -> GraphState:
    """
    Build a failed state when investigation planning fails.

    Args:
        state: Original state to preserve user_query and other data

    Returns:
        Updated GraphState with empty investigations list
    """
    logger.warning("🚨 Building failed state - no investigations created")

    return replace(state, investigations=[])
