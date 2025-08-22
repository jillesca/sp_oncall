"""
Network Executor Node.

This module orchestrates network operations for multiple device investigations
by executing commands concurrently via MCP agent and processing responses.
"""

# Import the main node function from core
from .core import llm_network_executor

# Import supporting functions for backwards compatibility with tests
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

# Aliases for backwards compatibility with tests
_log_incoming_state = log_incoming_state
_log_processed_data = log_processed_data
_execute_investigations_concurrently = execute_investigations_concurrently
_execute_single_investigation = execute_single_investigation
_build_investigation_context = build_investigation_context
_update_state_with_investigations = update_state_with_investigations
_update_state_with_global_error = update_state_with_global_error
_extract_response_content = extract_response_content
_extract_last_ai_message = extract_last_ai_message
_extract_tool_messages = extract_tool_messages
_convert_tool_message_to_executed_call = convert_tool_message_to_executed_call
