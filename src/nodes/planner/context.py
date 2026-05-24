"""Context building for per-device planning."""

from schemas.state import Investigation
from nodes.markdown_builder import MarkdownBuilder
from src.logging import get_logger

logger = get_logger(__name__)


def build_planning_context(
    investigation: Investigation,
    trigger_context: str,
    investigation_role: str,
) -> str:
    """
    Build planning context for a single device investigation.

    Args:
        investigation: The device investigation to plan for
        trigger_context: Original trigger content (alert or user request)
        investigation_role: "primary" for alert targets, "context" for neighbor checks

    Returns:
        Markdown-formatted string containing device details for the planner
    """
    logger.debug(
        "📋 Building planning context for device: %s (role=%s)",
        investigation.device_name,
        investigation_role,
    )

    builder = MarkdownBuilder()
    builder.add_header("Planning Context")

    builder.add_section("Trigger")
    builder.add_text(trigger_context)

    builder.add_section("Investigation Role")
    builder.add_text(investigation_role)

    builder.add_section("Device")
    builder.add_subsection(f"Device: `{investigation.device_name}`")
    builder.add_bold_text("Role:", investigation.role or "Unknown")
    builder.add_bold_text("Device Context:")
    builder.add_code_block(investigation.device_context or "No context available")

    context_string = builder.build()
    logger.debug(
        "📤 Planning context prepared (%d characters)", len(context_string)
    )
    return context_string
