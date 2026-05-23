"""Context building for per-device planning."""

from schemas.state import Investigation
from nodes.markdown_builder import MarkdownBuilder
from src.logging import get_logger

logger = get_logger(__name__)


def build_planning_context(investigation: Investigation) -> str:
    """
    Build planning context for a single device investigation.

    Args:
        investigation: The device investigation to plan for

    Returns:
        Markdown-formatted string containing device details for the planner
    """
    logger.debug(
        "📋 Building planning context for device: %s", investigation.device_name
    )

    builder = MarkdownBuilder()
    builder.add_header("Planning Context")
    builder.add_section("Device")
    builder.add_subsection(f"Device: `{investigation.device_name}`")
    builder.add_bold_text("Role:", investigation.role or "Unknown")
    builder.add_bold_text("Device Profile:")
    builder.add_code_block(investigation.device_profile or "No profile available")

    context_string = builder.build()
    logger.debug(
        "📤 Planning context prepared (%d characters)", len(context_string)
    )
    return context_string
