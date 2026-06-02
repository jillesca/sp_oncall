"""
Planner module.

Provides per-device planning logic: loads skills, selects an investigation
plan for a single device, and returns a flat DevicePlan. Planning is invoked
from within the phase sub-graphs rather than the outer graph.
"""

from .core import plan_single_device as plan_single_device
from .planning import DevicePlan as DevicePlan
