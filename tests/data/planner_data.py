"""
Test data for planner node tests.
Contains realistic data structures used in planner functions.
"""

from schemas.state import (
    GraphState,
    Investigation,
    InvestigationStatus,
    InvestigationPriority,
)
from src.nodes.planner.planning import DevicePlan, PlanningResponse

# Sample GraphState with investigations for planning
SAMPLE_GRAPH_STATE_FOR_PLANNING = GraphState(
    user_query="Check device health",
    investigations=[
        Investigation(
            device_name="xrd-1",
            device_profile='{"role": "PE", "is_mpls_enabled": true}',
            role="PE",
            objective=None,
            working_plan_steps="",
            execution_results=[],
            status=InvestigationStatus.PENDING,
            priority=InvestigationPriority.MEDIUM,
            dependencies=[],
            report=None,
            error_details=None,
        ),
        Investigation(
            device_name="xrd-2",
            device_profile='{"role": "P", "is_mpls_enabled": true}',
            role="P",
            objective=None,
            working_plan_steps="",
            execution_results=[],
            status=InvestigationStatus.PENDING,
            priority=InvestigationPriority.MEDIUM,
            dependencies=[],
            report=None,
            error_details=None,
        ),
    ],
    historical_context=[],
    max_retries=3,
    current_retries=0,
    assessment=None,
    final_report=None,
)

# Sample PlanningResponse for testing
SAMPLE_PLANNING_RESPONSE = PlanningResponse(
    plan=[
        DevicePlan(
            device_name="xrd-1",
            role="PE",
            objective="Check PE router health and MPLS status",
            working_plan_steps="Step 1: Check system info\nStep 2: Check MPLS status",
        ),
        DevicePlan(
            device_name="xrd-2",
            role="P",
            objective="Check P router health and core connectivity",
            working_plan_steps="Step 1: Check system info\nStep 2: Check interfaces",
        ),
    ]
)

# Empty planning response
EMPTY_PLANNING_RESPONSE = PlanningResponse(plan=[])

# Sample GraphState with no investigations
EMPTY_GRAPH_STATE_FOR_PLANNING = GraphState(
    user_query="test query",
    investigations=[],
    historical_context=[],
    max_retries=3,
    current_retries=0,
    assessment=None,
    final_report=None,
)

# Sample error for testing
SAMPLE_PLANNING_ERROR = RuntimeError("Planning failed")
