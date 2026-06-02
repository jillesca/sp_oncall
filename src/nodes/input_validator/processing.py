"""
Response processing for input validation.

This module handles parsing MCP agent responses into structured device data.
Investigation object creation and store hydration are handled by core.py.
"""

from typing import Any, List, Optional
from dataclasses import dataclass, field, replace

from langchain_core.messages import BaseMessage
from langchain_core.language_models import BaseChatModel

from schemas.device_capability_profile import DeviceCapabilityProfile
from src.util.validation import validate_structured_output, validate_investigation_planning
from src.logging import get_logger, debug_capture_object

logger = get_logger(__name__)


@dataclass
class DiscoveredDevice:
    """Device information returned by the device discovery MCP agent."""

    device_name: str
    is_primary: bool = False
    type_model: str = ""
    role: str = ""
    neighbors: List[str] = field(default_factory=list)
    capability_profile: Optional[DeviceCapabilityProfile] = None


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
        return InvestigationPlanningResponse(
            devices=[_to_discovered_device(d) for d in result.devices]
        )
    elif isinstance(result, dict) and "devices" in result:
        return InvestigationPlanningResponse(
            devices=[_to_discovered_device(d) for d in result["devices"] if d]
        )

    logger.error("❌ Unexpected response format: %s", type(result))
    return InvestigationPlanningResponse(devices=[])


def _to_discovered_device(device_data: Any) -> DiscoveredDevice:
    """Convert device data from the LLM parser into a typed DiscoveredDevice.

    LangChain's structured output parser does not coerce nested dicts into
    dataclass instances. This function handles both cases — a dict coming
    from the JSON branch and a DiscoveredDevice whose capability_profile
    field may still be a raw dict from the dataclass branch.
    """
    if isinstance(device_data, DiscoveredDevice):
        return replace(
            device_data,
            capability_profile=_to_capability_profile(device_data.capability_profile),
        )

    if isinstance(device_data, dict):
        return DiscoveredDevice(
            device_name=device_data.get("device_name", ""),
            is_primary=device_data.get("is_primary", False),
            type_model=device_data.get("type_model", ""),
            role=device_data.get("role", ""),
            neighbors=device_data.get("neighbors", []),
            capability_profile=_to_capability_profile(
                device_data.get("capability_profile")
            ),
        )

    logger.warning("⚠️ Unexpected device data type: %s", type(device_data))
    return DiscoveredDevice(device_name="")


def _to_capability_profile(data: Any) -> Optional[DeviceCapabilityProfile]:
    """Convert a raw dict or existing object into a DeviceCapabilityProfile.

    Returns None when no profile data is present so callers can treat the
    absence of a profile as an optional section without special-casing.
    """
    if data is None:
        return None

    if isinstance(data, DeviceCapabilityProfile):
        return data

    if isinstance(data, dict):
        return DeviceCapabilityProfile(
            nos=data.get("nos", ""),
            is_mpls_enabled=data.get("is_mpls_enabled", False),
            is_isis_enabled=data.get("is_isis_enabled", False),
            is_bgp_l3vpn_enabled=data.get("is_bgp_l3vpn_enabled", False),
            is_route_reflector=data.get("is_route_reflector", False),
            has_vpn_ipv4_unicast_bgp=data.get("has_vpn_ipv4_unicast_bgp", False),
        )

    logger.warning("⚠️ Unexpected capability_profile type: %s", type(data))
    return None


