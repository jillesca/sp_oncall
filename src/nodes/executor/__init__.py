"""
Network Executor — investigation phase sub-graphs and enrichment.

Each sub-graph exposes the same four internal nodes visible in LangGraph Studio:
  plan_device → execute_device → assess_device → [retry] → collect_device_result

Both sub-graphs handle all devices for their phase in a single agent call
(Option B), with the phase helper logic shared via phase.py.

Exports:
  context_investigation_subgraph  : compiled sub-graph for context device phase
  enrich_primary_investigations   : parent-graph node injecting context findings
  primary_investigation_subgraph  : compiled sub-graph for primary device phase
"""

from .context_investigation import context_investigation_subgraph
from .primary_investigation import (
    enrich_primary_investigations,
    primary_investigation_subgraph,
)

__all__ = [
    "context_investigation_subgraph",
    "enrich_primary_investigations",
    "primary_investigation_subgraph",
]
