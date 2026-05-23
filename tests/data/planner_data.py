"""
Test data for planner node tests.
Contains realistic data structures used in planner functions.
"""

from langchain_core.messages import HumanMessage

from schemas.state import GraphState, Investigation, InvestigationStatus
from src.nodes.planner.planning import DevicePlan, PlanningResponse

SAMPLE_GRAPH_STATE_FOR_PLANNING = GraphState(
    messages=[HumanMessage(content="Check device health")],
    investigations=[
        Investigation(
            device_name="xrd-1",
            device_profile='{"role": "PE", "is_mpls_enabled": true}',
            role="PE",
            objective=None,
            working_plan_steps="",
            execution_results=[],
            status=InvestigationStatus.PENDING,
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
            report=None,
            error_details=None,
        ),
    ],
)

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

EMPTY_PLANNING_RESPONSE = PlanningResponse(plan=[])

EMPTY_GRAPH_STATE_FOR_PLANNING = GraphState(
    messages=[HumanMessage(content="test query")],
    investigations=[],
)

SAMPLE_PLANNING_ERROR = RuntimeError("Planning failed")
