"""
Input Validator Node.

This module orchestrates the multi-device investigation setup workflow by
extracting device information and creating Investigation objects.
"""

# Import the main node function from core
from .core import (
    input_validator_node,
    _log_successful_investigation_planning,
    _build_failed_state,
)

# Import supporting functions for backwards compatibility with tests
from .extraction import (
    execute_investigation_planning,
    extract_mcp_response_content,
)
from .processing import (
    process_investigation_planning_response,
    create_investigations_from_response,
    InvestigationPlanningResponse,
    DeviceToInvestigate,
    _normalize_device_profile,
)
from nodes.common import load_model

# Aliases for backwards compatibility with tests
_load_model = lambda: load_model()
_execute_investigation_planning = execute_investigation_planning
_extract_mcp_response_content = extract_mcp_response_content
_process_investigation_planning_response = (
    process_investigation_planning_response
)
# _normalize_device_profile is already imported above
# These are defined in this module so we reference them directly
# _log_successful_investigation_planning and _build_failed_state are defined below

# Add the missing aliases here after function definitions
_create_investigations_from_response = create_investigations_from_response
