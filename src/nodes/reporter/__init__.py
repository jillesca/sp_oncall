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

# Import supporting functions
from .context import (
    build_report_context,
    _add_single_investigation_details,
    _add_historical_context,
)
from .generation import generate_report, _extract_report_content
from .session import (
    update_workflow_session,
    _build_learning_insights_context,
    _generate_learning_insights_with_llm,
)
from nodes.common import load_model
