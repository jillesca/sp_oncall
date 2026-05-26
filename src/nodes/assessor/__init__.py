"""
Objective Assessor.

Provides assessment workflow functions used by the phase sub-graphs
inside the executor.
"""

from .context import build_phase_assessment_context as build_phase_assessment_context
from .assessment import execute_assessment as execute_assessment
