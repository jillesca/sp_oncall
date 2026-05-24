"""
Response processing for input validation.

This module handles processing MCP responses to extract device information
and create Investigation objects with full device context.
"""

from typing import List
from dataclasses import dataclass, field

from langchain_core.messages import BaseMessage
from langchain_core.language_models import BaseChatModel

from schemas.state import Investigation
from src.util.validation import validate_structured_output, validate_investigation_planning
from src.logging import get_logger, debug_capture_object

logger = get_logger(__name__)


@dataclass
class DiscoveredDevice:
    """Device information returned by the device discovery MCP agent."""

    device_name: str
    type_model: str = ""
    role: str = ""
    neighbors: List[str] = field(default_factory=list)


@dataclass
class InvestigationPlanningResponse:
    """Schema for device discovery output from the input validator."""

    devices: List[DiscoveredDevice]

    def __len__(self) -> int:
        return len(self.devices)

    def __iter__(self):
        return iter(self.devices)


def process_investigation_planning_response(
    response_content: BaseMessage, model: BaseChatModel
) -> InvestigationPlanningResponse:
    """
    Parses the MCP agent response content for device discovery.

    Args:
        response_content: Content from MCP agent response
        model: LLM model for structured output parsing

    Returns:
        InvestigationPlanningResponse with discovered devices and their profiles
    """
    logger.debug("🧠 Getting structured output")

    result, violations = validate_structured_output(
        raw_text=response_content.content,
        schema=InvestigationPlanningResponse,
        model=model,
        validators=[validate_investigation_planning],
    )

    logger.debug("📋 Structured output captured: %s", result)
    debug_capture_object(result, label="_process_investigation_planning_response")

    if violations:
        logger.warning(
            "⚠️ Investigation planning validation violations: %s", violations
        )

    if isinstance(result, InvestigationPlanningResponse):
        return result
    elif isinstance(result, dict) and "devices" in result:
        devices = [
            DiscoveredDevice(**d) if isinstance(d, dict) else d
            for d in result["devices"]
            if d
        ]
        return InvestigationPlanningResponse(devices=devices)

    logger.error("❌ Unexpected response format: %s", type(result))
    return InvestigationPlanningResponse(devices=[])


def create_investigations_from_response(
    planning_response: InvestigationPlanningResponse,
) -> List[Investigation]:
    """
    Create Investigation objects from the device discovery response.

    Populates device_profile, role, and neighbors from the discovery data.
    The executor will further enrich device_profile with stored facts before
    execution.

    Args:
        planning_response: The parsed response containing discovered devices

    Returns:
        List of Investigation objects, one for each discovered device
    """
    logger.debug(
        "🏗️ Creating %d Investigation objects from planning response",
        len(planning_response),
    )

    investigations = []
    for device in planning_response:
        investigation = Investigation(
            device_name=device.device_name,
            device_profile=device.type_model,
            role=device.role,
            neighbors=device.neighbors,
        )
        investigations.append(investigation)
        logger.debug(
            "  ✅ Created investigation for %s (role=%s, neighbors=%s)",
            device.device_name,
            device.role,
            device.neighbors,
        )

    return investigations
