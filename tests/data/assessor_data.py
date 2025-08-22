"""
Test data for assessor node tests.
Reorganized from existing assessor test files for better reusability.
"""

from schemas.state import (
    GraphState,
    Investigation,
    InvestigationStatus,
    InvestigationPriority,
)
from schemas.assessment_schema import AssessmentOutput

# Sample GraphState with investigations for assessment context building
SAMPLE_GRAPH_STATE_WITH_INVESTIGATIONS = GraphState(
    user_query="how are my routers PE doing?",
    investigations=[
        Investigation(
            device_name="xrd-1",
            device_profile="is_mpls_enabled=true; is_isis_enabled=true; is_bgp_l3vpn_enabled=true; is_route_reflector=false; has_vpn_ipv4_unicast_bgp=true; role=PE",
            role="PE",
            objective="Assess health and VPN/MPLS/BGP/L3VPN status for PE router xrd-1",
            working_plan_steps="Step 1: Review session history and prior investigation results",
            execution_results=[],
            status=InvestigationStatus.COMPLETED,
            priority=InvestigationPriority.MEDIUM,
            dependencies=[],
            report="Sample investigation report for xrd-1",
            error_details=None,
        ),
        Investigation(
            device_name="xrd-2",
            device_profile="is_mpls_enabled=true; is_isis_enabled=true; is_bgp_l3vpn_enabled=true; is_route_reflector=false; has_vpn_ipv4_unicast_bgp=true; role=PE",
            role="PE",
            objective="Assess health and VPN/MPLS/BGP/L3VPN status for PE router xrd-2",
            working_plan_steps="Step 1: Review session history and prior investigation results",
            execution_results=[],
            status=InvestigationStatus.COMPLETED,
            priority=InvestigationPriority.MEDIUM,
            dependencies=[],
            report="Sample investigation report for xrd-2",
            error_details=None,
        ),
    ],
    workflow_session=[],
    max_retries=3,
    current_retries=0,
    assessment=None,
    final_report=None,
)

# Sample AssessmentOutput for testing format ensuring
SAMPLE_ASSESSMENT_OUTPUT = AssessmentOutput(
    is_objective_achieved=True,
    notes_for_final_report="Assessment completed successfully",
    feedback_for_retry=None,
)

# Sample assessment output as dict (from LLM response)
SAMPLE_ASSESSMENT_DICT = {
    "is_objective_achieved": True,
    "notes_for_final_report": "Assessment completed successfully",
    "feedback_for_retry": None,
}

# Empty state for testing
EMPTY_GRAPH_STATE = GraphState(
    user_query="test query",
    investigations=[],
    workflow_session=[],
    max_retries=3,
    current_retries=0,
    assessment=None,
    final_report=None,
)

# State with retry context
RETRY_GRAPH_STATE = GraphState(
    user_query="test query with retry",
    investigations=[],
    workflow_session=[],
    max_retries=3,
    current_retries=1,
    assessment=AssessmentOutput(
        is_objective_achieved=False,
        notes_for_final_report="First attempt failed",
        feedback_for_retry="Try a different approach",
    ),
    final_report=None,
)
