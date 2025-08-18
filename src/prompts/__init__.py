"""Prompt templates package.

This package contains one file per prompt for easy discoverability.
"""

# Optionally re-export common names for convenience
from .report_generator import REPORT_GENERATOR_PROMPT_TEMPLATE  # noqa: F401
from .objective_assessor import OBJECTIVE_ASSESSOR_PROMPT  # noqa: F401
from .network_executor import NETWORK_EXECUTOR_PROMPT  # noqa: F401
from .investigation_planning import INVESTIGATION_PLANNING_PROMPT  # noqa: F401
from .planner import PLANNER_PROMPT  # noqa: F401
