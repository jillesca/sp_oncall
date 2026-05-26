"""
Context building for executor investigations.

Builds the investigation context passed to the MCP executor agent.
Data sections are wrapped in XML tags so the LLM has explicit scope
boundaries between instructions (markdown) and injected data (XML+markdown).

Each device's context is labelled with its name so the executor and the
resulting report can clearly attribute findings per device.
"""

from schemas import Investigation
from src.util.xml_helpers import xml_wrap
from src.logging import get_logger

logger = get_logger(__name__)


def build_phase_context(
    investigation: Investigation,
    trigger_context: str,
    context_phase_report: str = "",
) -> str:
    """Build combined context for all devices in an investigation phase.

    Produces a single document covering every device in the phase so the
    executor agent has full situational awareness in one prompt.

    Structure:
    1. TRIGGER_CONTEXT — what triggered this investigation
    2. NEIGHBOR_HEALTH_CHECK_RESULTS — neighbor findings (primary phase only)
    3. Summary line listing all devices under investigation
    4. One DEVICE block per device — plan and device context, clearly labelled
    """
    sections = [xml_wrap("TRIGGER_CONTEXT", trigger_context)]

    if context_phase_report:
        sections.append(
            xml_wrap("NEIGHBOR_HEALTH_CHECK_RESULTS", context_phase_report)
        )

    device_names = investigation.device_names()
    sections.append(f"**Devices to investigate:** {', '.join(device_names)}")

    for device_name, device_context in investigation.device_contexts.items():
        device_plan = investigation.device_plans.get(device_name, "")
        sections.append(_build_device_section(device_name, device_context, device_plan))

    return "\n\n".join(sections)


def _build_device_section(
    device_name: str,
    device_context: str,
    device_plan: str,
) -> str:
    """Build a self-contained XML block for one device investigation.

    The device name in the opening tag makes it unambiguous which device
    each block belongs to so the executor report can clearly identify findings
    per device.
    """
    lines = [f'<DEVICE name="{device_name}">']

    if device_plan:
        lines.append(device_plan)

    lines.append(xml_wrap("DEVICE_CONTEXT", device_context))
    lines.append("</DEVICE>")

    return "\n".join(lines)
