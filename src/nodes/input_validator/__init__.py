"""
Input Validator Node.

This module orchestrates the multi-device investigation setup workflow by
extracting device information and creating Investigation objects.
"""

from .core import (
    input_validator_node,
    _log_successful_investigation_planning,
    _build_failed_state,
)

from .extraction import (
    execute_investigation_planning,
    extract_mcp_response_content,
    build_investigation_planning_context,
)
from .processing import (
    process_investigation_planning_response,
    InvestigationPlanningResponse,
)
from nodes.common import load_model
