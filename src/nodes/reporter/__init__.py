"""
Investigation Reporter Node.

This module orchestrates the complete report generation workflow.
"""

from .core import investigation_report_node
from .context import build_report_context
from .generation import generate_report
from nodes.common import load_model
