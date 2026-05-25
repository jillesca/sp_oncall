"""
Node modules for the SP On-Call LangGraph workflow.

This package contains all the node implementations that form the graph workflow:
- input_validator: Validates input, discovers devices, splits primary vs context
- executor: Dispatch functions and compiled device sub-graphs.
            context_device_subgraph / primary_device_subgraph are the expandable
            sub-graphs visible in LangSmith Studio.
            dispatch_context_investigations / dispatch_primary_investigations fan
            out via Send; primary_dispatch_node enriches primaries with context
            reports before the primary phase.
- rca_assessor: Synthesizes all reports into a root cause determination
- reporter: Generates the final formatted report and persists to store
- assessor: Per-device objective assessment (used inside device_subgraph)
- markdown_builder: Utility for building markdown content
- common: Shared utilities across all nodes
"""

from .input_validator import input_validator_node
from .rca_assessor import rca_assessor_node
from .reporter import investigation_report_node

__all__ = [
    "input_validator_node",
    "rca_assessor_node",
    "investigation_report_node",
]
