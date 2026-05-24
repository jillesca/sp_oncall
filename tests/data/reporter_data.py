"""
Test data for reporter node tests.
Contains realistic data structures used in reporter functions.
"""

from langchain_core.messages import AIMessage, HumanMessage

from schemas.state import GraphState, Investigation, InvestigationStatus

SAMPLE_GRAPH_STATE_FOR_REPORTING = GraphState(
    messages=[HumanMessage(content="Check device health")],
    investigations=[
        Investigation(
            device_name="xrd-1",
            device_context="PE router profile",
            role="PE",
            objective="Check device health",
            working_plan_steps="Step 1: Check system info",
            execution_results=[],
            status=InvestigationStatus.COMPLETED,
            report="Device xrd-1 is healthy",
            error_details=None,
        ),
        Investigation(
            device_name="xrd-2",
            device_context="P router profile",
            role="P",
            objective="Check device health",
            working_plan_steps="Step 1: Check system info",
            execution_results=[],
            status=InvestigationStatus.FAILED,
            report=None,
            error_details="Connection timeout",
        ),
    ],
)

EMPTY_GRAPH_STATE_FOR_REPORTING = GraphState(
    messages=[HumanMessage(content="test query")],
    investigations=[],
)

SAMPLE_AI_RESPONSE = AIMessage(
    content="Generated report content",
    id="test-response",
)

SAMPLE_AI_RESPONSE_LIST = AIMessage(
    content=["Part 1 of report", "Part 2 of report"],
    id="test-response-list",
)

SAMPLE_FINAL_REPORT = "This is a generated final report"
