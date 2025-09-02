"""
Response processing for input validation.

This module handles processing MCP responses to extract device information
and create Investigation objects.
"""

import json
from typing import List
from dataclasses import dataclass

from langchain_core.messages import BaseMessage
from langchain_core.language_models import BaseChatModel

from schemas.state import Investigation
from src.logging import get_logger, debug_capture_object

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
        return len(self.devices)

    def __iter__(self):
        return iter(self.devices)


def process_investigation_planning_response(
    response_content: BaseMessage, model: BaseChatModel
) -> InvestigationPlanningResponse:
    """
    Parses the MCP agent response content for investigation planning.

    Args:
        response_content: Content from MCP agent response
        model: LLM model for processing the response

    Returns:
        InvestigationPlanningResponse with extracted device information
    """
    logger.debug("🧠 Getting structured output")

    try:
        # Use the model to process the response and extract device names
        response = model.with_structured_output(
            schema=InvestigationPlanningResponse
        ).invoke(input=response_content.content)

        logger.debug("📋 Structured output captured: %s", response)
        debug_capture_object(
            response, label="_process_investigation_planning_response"
        )

        logger.debug("🎯 Extracted device names: %s", response)

        # Ensure we have a proper InvestigationPlanningResponse object
        if isinstance(response, InvestigationPlanningResponse):
            return _normalize_investigation_response(response)
        elif isinstance(response, dict) and "devices" in response:
            return _create_response_from_dict(response)
        else:
            logger.error("❌ Unexpected response format: %s", type(response))
            return InvestigationPlanningResponse(devices=[])

    except Exception as e:
        logger.error("❌ LLM processing failed: %s", e)
        return InvestigationPlanningResponse(devices=[])


def create_investigations_from_response(
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
            role=device.role,
        )
        investigations.append(investigation)
        logger.debug(
            "  ✅ Created investigation for device: %s (role: %s)",
            device.device_name,
            device.role,
        )

    return investigations


def _normalize_investigation_response(
    response: InvestigationPlanningResponse,
) -> InvestigationPlanningResponse:
    """Normalize device profiles in investigation response."""
    normalized_devices = []
    for device in response.devices:
        normalized_device = DeviceToInvestigate(
            device_name=device.device_name,
            device_profile=_normalize_device_profile(device.device_profile),
            role=device.role,
        )
        normalized_devices.append(normalized_device)
    return InvestigationPlanningResponse(devices=normalized_devices)


def _create_response_from_dict(
    response: dict,
) -> InvestigationPlanningResponse:
    """Create InvestigationPlanningResponse from dictionary."""
    investigations_data = response["devices"]
    devices = [
        (
            DeviceToInvestigate(
                device_name=item["device_name"],
                device_profile=_normalize_device_profile(
                    item["device_profile"]
                ),
                role=item.get("role", ""),
            )
            if isinstance(item, dict)
            else item
        )
        for item in investigations_data
    ]
    return InvestigationPlanningResponse(devices=devices)


def _normalize_device_profile(device_profile) -> str:
    """
    Normalize device_profile to a consistent string format.

    Args:
        device_profile: The device profile value from LLM response

    Returns:
        String representation of the device profile
    """
    if device_profile is None:
        logger.debug("🔄 Normalizing None device_profile to 'unknown'")
        return "unknown"

    if isinstance(device_profile, str):
        normalized = device_profile.strip()
        if not normalized:
            logger.debug(
                "🔄 Normalizing empty string device_profile to 'unknown'"
            )
            return "unknown"
        logger.debug("🔄 Using string device_profile: %s", normalized)
        return normalized

    if isinstance(device_profile, dict):
        # Handle empty dict case
        if not device_profile:
            logger.debug(
                "🔄 Normalizing empty dict device_profile to 'unknown'"
            )
            return "unknown"

        # Convert entire dictionary to JSON string to preserve all information
        try:
            result = json.dumps(device_profile, sort_keys=True)
            logger.debug(
                "🔄 Converted dict device_profile to JSON string: %s", result
            )
            return result
        except (TypeError, ValueError) as e:
            # Fallback to string representation if JSON serialization fails
            result = str(device_profile).strip()
            logger.debug(
                "🔄 JSON serialization failed, using string representation: %s",
                result,
            )
            return result if result else "unknown"

    # Handle any other type by converting to string
    result = str(device_profile).strip()
    logger.debug(
        "🔄 Converted %s device_profile to string: %s",
        type(device_profile).__name__,
        result,
    )
    return result if result else "unknown"
