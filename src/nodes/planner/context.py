"""Context building for per-device planning."""

from src.util.xml_helpers import xml_wrap
from src.logging import get_logger

logger = get_logger(__name__)


def build_planning_context(
    device_name: str,
    device_context: str,
    trigger_context: str,
    investigation_role: str,
) -> str:
    """Build planning context for a single device investigation.

    Data sections (trigger, device context) are XML-wrapped so the planner
    LLM can distinguish injected data from its instructions.

    Args:
        device_name: Target device identifier.
        device_context: Pre-formatted context string for this device.
        trigger_context: Original trigger content (alert or user request).
        investigation_role: "primary" for alert targets, "context" for neighbor checks.

    Returns:
        Formatted string containing device details for the planner.
    """
    logger.debug(
        "📋 Building planning context for device: %s (role=%s)",
        device_name,
        investigation_role,
    )

    context_string = "\n\n".join(
        [
            f"**Investigation Role:** {investigation_role}",
            f"**Device:** `{device_name}`",
            xml_wrap("TRIGGER_CONTEXT", trigger_context),
            xml_wrap("DEVICE_CONTEXT", device_context or "No context available"),
        ]
    )

    logger.debug(
        "📤 Planning context prepared (%d characters)", len(context_string)
    )
    return context_string
