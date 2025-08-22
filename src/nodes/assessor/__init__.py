"""
Objective Assessor Node.

This module orchestrates the assessment workflow by evaluating investigations
and determining workflow completion status.
"""

# Import the main node function from core
from .core import objective_assessor_node

# Import supporting functions for backwards compatibility with tests
from .context import (
    build_assessment_context,
    _add_investigation_details as _add_investigation_to_builder,
    _add_session_context_to_builder,
    _add_execution_results_to_builder,
    _add_previous_report_to_builder,
    _add_learned_patterns_to_builder,
    _add_device_relationships_to_builder,
)
from .assessment import execute_assessment, ensure_proper_assessment_format
from .state import (
    apply_assessment_to_workflow,
    handle_assessment_error,
    _build_successful_assessment_state,
    _build_retry_or_failed_assessment_state,
    _build_retry_state,
    _build_max_retries_reached_state,
    _build_error_retry_state,
    _build_error_final_state,
    _get_encouraging_retry_guidance,
)

# Aliases for backwards compatibility with tests
_build_assessment_context = build_assessment_context
_ensure_proper_assessment_format = ensure_proper_assessment_format
_apply_assessment_to_workflow = apply_assessment_to_workflow
_handle_assessment_error = handle_assessment_error
