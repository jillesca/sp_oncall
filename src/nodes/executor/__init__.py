"""
Network Executor — investigation phase sub-graphs.

Each sub-graph exposes the same four internal nodes visible in LangGraph Studio:
  plan_device → execute_device → assess_device → [retry] → collect_device_result

Both sub-graphs handle all devices for their phase in a single agent call,
with the phase helper logic shared via phase.py.

The primary sub-graph reads context_phase_report directly from GraphState via
LangGraph field mapping, eliminating the need for a separate enrichment node.

Exports:
  context_investigation_subgraph  : compiled sub-graph for context device phase
  primary_investigation_subgraph  : compiled sub-graph for primary device phase
"""

from .context_investigation import context_investigation_subgraph
from .primary_investigation import primary_investigation_subgraph

__all__ = [
    "context_investigation_subgraph",
    "primary_investigation_subgraph",
]
