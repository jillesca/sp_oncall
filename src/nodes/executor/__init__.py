"""
Network Executor — device sub-graph dispatch.

Exports:
- context_device_subgraph / primary_device_subgraph: compiled LangGraph
  sub-graphs added as named nodes in the orchestrator so they appear as
  expandable boxes in LangSmith Studio.
- context_dispatcher / primary_dispatcher: graph nodes that fan out via
  Command(goto=[Send(...)]) to the respective sub-graphs.
- route_from_input_validator / route_after_context_phase: conditional edge
  functions that return plain strings for readable routing decisions.
"""

from .core import (
    context_dispatcher,
    primary_dispatcher,
    route_from_input_validator,
    route_after_context_phase,
)
from .device_subgraph import (
    context_device_subgraph,
    primary_device_subgraph,
)
