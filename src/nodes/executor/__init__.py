"""
Network Executor — device sub-graph dispatch.

Exports:
- context_device_subgraph / primary_device_subgraph: compiled LangGraph
  sub-graphs added as named nodes in the orchestrator so they appear as
  expandable boxes in LangSmith Studio.
- dispatch_context_investigations / dispatch_primary_investigations: conditional
  edge functions that fan out via Send to the respective sub-graphs.
- primary_dispatch_node: regular node that enriches primary investigations
  with context reports before the primary dispatch fan-out.
"""

from .core import (
    dispatch_context_investigations,
    dispatch_primary_investigations,
    primary_dispatch_node,
)
from .device_subgraph import (
    context_device_subgraph,
    primary_device_subgraph,
)
