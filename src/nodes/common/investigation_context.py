"""
Shared context formatting for investigation reports.

Used by both the RCA assessor and the reporter to format investigation
findings for LLM consumption. Centralised here so changes to formatting
apply to both consumers from one location.
"""

from typing import List

from schemas.state import Investigation


def format_primary_reports(investigations: List[Investigation]) -> str:
    """Format primary investigation reports for LLM context.

    Each investigation covers all primary devices in the phase and produces
    one combined report. The device names and status are shown as a header.
    """
    parts = []
    for inv in investigations:
        device_names = ", ".join(inv.device_names())
        lines = [f"### Devices: {device_names} (status: {inv.status.value})"]
        if inv.report:
            lines.append(inv.report)
        elif inv.error_details:
            lines.append(f"**Error:** {inv.error_details}")
        else:
            lines.append("No report available.")
        parts.append("\n".join(lines))
    return "\n\n---\n\n".join(parts)


def format_context_phase_section(
    phase_report: str,
    device_names: List[str],
) -> str:
    """Format the combined context phase report with a device summary header."""
    device_list = ", ".join(device_names)
    return f"**Devices checked:** {device_list}\n\n{phase_report}"
