"""
Node modules for the SP On-Call LangGraph workflow.

Graph flow (linear, no conditional edges):
  input_validator
      → context_investigation   (subgraph: one agent for all context devices)
      → enrich_primary_investigations   (node: injects context findings)
      → primary_investigation   (subgraph: one agent for all primary devices)
      → rca_assessor
      → report_generator

Modules:
- input_validator: Validates input, discovers devices, splits primary vs context
- executor: Phase sub-graphs (context_investigation, primary_investigation) and
            the enrich_primary_investigations enrichment node.
- rca_assessor: Synthesizes all reports into a root cause determination
- reporter: Generates the final formatted report and persists to store
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
