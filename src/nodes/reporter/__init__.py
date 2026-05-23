"""
Investigation Reporter Node.

This module orchestrates the complete report generation workflow.
"""

from .core import (
    investigation_report_node,
    _log_successful_report_generation,
)
from .context import (
    build_report_context,
    _add_single_investigation_details,
)
from .generation import generate_report, _extract_report_content
from nodes.common import load_model
