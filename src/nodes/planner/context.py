"""Context building for per-device planning."""

from schemas.state import Investigation
from src.util.xml_helpers import xml_wrap
from src.logging import get_logger

logger = get_logger(__name__)


def build_planning_context(
    investigation: Investigation,
    trigger_context: str,
    investigation_role: str,
) -> str:
    """Build planning context for a single device investigation.

    Data sections (trigger, device context) are XML-wrapped so the planner
    LLM can distinguish injected data from its instructions.

    Args:
        investigation: The device investigation to plan for.
        trigger_context: Original trigger content (alert or user request).
        investigation_role: "primary" for alert targets, "context" for neighbor checks.

    Returns:
        Formatted string containing device details for the planner.
    """
    logger.debug(
        "📋 Building planning context for device: %s (role=%s)",
        investigation.device_name,
        investigation_role,
    )

    device_context_content = investigation.device_context or "No context available"

    context_string = "\n\n".join(
        [
            f"**Investigation Role:** {investigation_role}",
            f"**Device:** `{investigation.device_name}` (role: {investigation.role or 'Unknown'})",
            xml_wrap("TRIGGER_CONTEXT", trigger_context),
            xml_wrap("DEVICE_CONTEXT", device_context_content),
        ]
    )

    logger.debug(
        "📤 Planning context prepared (%d characters)", len(context_string)
    )
    return context_string
