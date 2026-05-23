"""
Objective Assessor Node.

This module orchestrates the assessment workflow by evaluating investigations
and determining workflow completion status.
"""

from .core import objective_assessor_node
from .context import (
    build_assessment_context,
    _add_investigation_details as _add_investigation_to_builder,
    _add_execution_results_to_builder,
)
from .assessment import execute_assessment, ensure_proper_assessment_format
