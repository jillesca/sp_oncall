"""
Network Executor Nodes.

Two dedicated nodes handle investigations in sequence:
- context_executor_node: neighbor health checks (run first, concurrently)
- primary_executor_node: alert target investigations (run second, concurrently,
  with access to context device reports)
"""

from .core import context_executor_node, primary_executor_node
from .logging import log_incoming_state, log_processed_data
from .execution import execute_single_investigation
from .state import (
    update_context_investigations,
    update_primary_investigations,
    mark_all_failed,
)
from .context import build_investigation_context, build_primary_investigation_context
from .device_subgraph import DeviceState, device_subgraph
from .processing import (
    extract_response_content,
    extract_last_ai_message,
    extract_tool_messages,
    convert_tool_message_to_executed_call,
)
