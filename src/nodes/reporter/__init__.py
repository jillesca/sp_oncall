"""
Investigation Reporter Node.

This module orchestrates the complete report generation workflow including
learning insights generation and workflow session management.
"""

# Import the main node function from core
from .core import (
    investigation_report_node,
    _log_successful_report_generation,
    _build_reset_state_with_report,
)

# Import supporting functions for backwards compatibility with tests
from .context import (
    build_report_context,
    _add_single_investigation_details,
    _add_session_context,
)
from .generation import generate_report, _extract_report_content
from .session import (
    update_workflow_session,
    _build_learning_insights_context,
    _generate_learning_insights_with_llm,
)
from nodes.common import load_model

# Aliases for backwards compatibility with tests
_build_report_context = build_report_context
_add_investigation_details = _add_single_investigation_details
_add_session_context = _add_session_context
_build_learning_insights_context = _build_learning_insights_context
_generate_learning_insights_with_llm = _generate_learning_insights_with_llm
_setup_report_model = lambda: load_model()
_generate_report = generate_report
_extract_report_content = _extract_report_content
_update_workflow_session = update_workflow_session
# These functions are defined in this module, will be aliased after definition
