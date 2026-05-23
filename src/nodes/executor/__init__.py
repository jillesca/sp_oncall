"""
Network Executor Node.

This module orchestrates network operations for multiple device investigations
by running a per-device sub-graph for each concurrently and merging results.
"""

from .core import llm_network_executor
from .logging import log_incoming_state, log_processed_data
from .execution import execute_single_investigation
from .state import update_state_with_investigations, update_state_with_global_error
from .context import build_investigation_context
from .device_subgraph import DeviceState, device_subgraph
from .processing import (
    extract_response_content,
    extract_last_ai_message,
    extract_tool_messages,
    convert_tool_message_to_executed_call,
)
