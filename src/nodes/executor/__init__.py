"""
Network Executor Node.

This module orchestrates network operations for multiple device investigations
by executing commands concurrently via MCP agent and processing responses.
"""

# Import the main node function from core
from .core import llm_network_executor

# Import supporting functions
from .logging import log_incoming_state, log_processed_data
from .execution import (
    execute_investigations_concurrently,
    execute_single_investigation,
)
from .state import (
    update_state_with_investigations,
    update_state_with_global_error,
)
from .context import build_investigation_context
from .processing import (
    extract_response_content,
    extract_last_ai_message,
    extract_tool_messages,
    convert_tool_message_to_executed_call,
)
