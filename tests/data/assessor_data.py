"""
Test data for assessor node tests.
"""

from langchain_core.messages import HumanMessage

from schemas.state import GraphState, Investigation, InvestigationStatus
from schemas.assessment_schema import AssessmentOutput

SAMPLE_TRIGGER_CONTEXT = "how are my routers PE doing?"

SAMPLE_INVESTIGATION_XRD1 = Investigation(
    device_name="xrd-1",
    device_context="is_mpls_enabled=true; is_isis_enabled=true; is_bgp_l3vpn_enabled=true; is_route_reflector=false; has_vpn_ipv4_unicast_bgp=true; role=PE",
    role="PE",
    objective="Assess health and VPN/MPLS/BGP/L3VPN status for PE router xrd-1",
    working_plan_steps="Step 1: Review session history and prior investigation results",
    execution_results=[],
    status=InvestigationStatus.COMPLETED,
    report="Sample investigation report for xrd-1",
    error_details=None,
)

SAMPLE_INVESTIGATION_XRD2 = Investigation(
    device_name="xrd-2",
    device_context="is_mpls_enabled=true; is_isis_enabled=true; is_bgp_l3vpn_enabled=true; is_route_reflector=false; has_vpn_ipv4_unicast_bgp=true; role=PE",
    role="PE",
    objective="Assess health and VPN/MPLS/BGP/L3VPN status for PE router xrd-2",
    working_plan_steps="Step 1: Review session history and prior investigation results",
    execution_results=[],
    status=InvestigationStatus.COMPLETED,
    report="Sample investigation report for xrd-2",
    error_details=None,
)

SAMPLE_GRAPH_STATE_WITH_INVESTIGATIONS = GraphState(
    messages=[HumanMessage(content=SAMPLE_TRIGGER_CONTEXT)],
    primary_investigations=[SAMPLE_INVESTIGATION_XRD1, SAMPLE_INVESTIGATION_XRD2],
)

SAMPLE_ASSESSMENT_OUTPUT = AssessmentOutput(
    is_objective_achieved=True,
    notes_for_final_report="Assessment completed successfully",
    feedback_for_retry=None,
)

SAMPLE_ASSESSMENT_DICT = {
    "is_objective_achieved": True,
    "notes_for_final_report": "Assessment completed successfully",
    "feedback_for_retry": None,
}

EMPTY_GRAPH_STATE = GraphState(
    messages=[HumanMessage(content="test query")],
)
