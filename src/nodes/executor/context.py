"""
Context building for executor investigations.

Builds the investigation context passed to the MCP executor agent.
Data sections are wrapped in XML tags so the LLM has explicit scope
boundaries between instructions (markdown) and injected data (XML+markdown).
"""

from typing import List

from schemas import Investigation
from src.util.xml_helpers import xml_wrap
from src.logging import get_logger

logger = get_logger(__name__)


def build_phase_context(
    investigations: List[Investigation],
    trigger_context: str,
) -> str:
    """Build combined context for all devices in an investigation phase.

    Produces a single document covering every device in the phase so the
    executor agent has full situational awareness in one prompt.

    Structure:
    1. TRIGGER_CONTEXT — what triggered this investigation
    2. NEIGHBOR_HEALTH_CHECK_RESULTS — neighbor findings (primary phase only)
    3. One DEVICE block per investigation — objective, plan, device context
    """
    sections = [xml_wrap("TRIGGER_CONTEXT", trigger_context)]

    neighbor_section = _build_neighbor_results_section(investigations)
    if neighbor_section:
        sections.append(neighbor_section)

    device_list = ", ".join(
        f"{inv.device_name} ({inv.role})" for inv in investigations
    )
    sections.append(f"**Devices to investigate:** {device_list}")

    for inv in investigations:
        sections.append(_build_device_section(inv))

    return "\n\n".join(sections)


def _build_neighbor_results_section(
    investigations: List[Investigation],
) -> str:
    """Return the NEIGHBOR_HEALTH_CHECK_RESULTS section, or empty string if absent.

    All primary investigations share the same context_phase_report as their
    neighbor_context. Deduplication ensures the combined report appears once
    even when multiple primary devices are investigated.
    """
    seen: set = set()
    parts = []
    for inv in investigations:
        if inv.neighbor_context and inv.neighbor_context not in seen:
            seen.add(inv.neighbor_context)
            parts.append(inv.neighbor_context)
    if not parts:
        return ""
    return xml_wrap("NEIGHBOR_HEALTH_CHECK_RESULTS", "\n\n".join(parts))


def _build_device_section(inv: Investigation) -> str:
    """Build a self-contained XML block for one device investigation."""
    lines = [
        f'<DEVICE name="{inv.device_name}" role="{inv.role}">',
        f"**Objective:** {inv.objective or 'Not specified'}",
    ]

    if inv.working_plan_steps:
        lines.append(xml_wrap("WORKING_PLAN", inv.working_plan_steps))

    lines.append(xml_wrap("DEVICE_CONTEXT", inv.device_context))
    lines.append("</DEVICE>")

    return "\n".join(lines)


