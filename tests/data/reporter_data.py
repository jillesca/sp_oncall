"""
Test data for reporter node tests.
Contains realistic data structures used in reporter functions.
"""

from schemas.state import (
    GraphState,
    Investigation,
    InvestigationStatus,
    InvestigationPriority,
    HistoricalContext,
)
from schemas.assessment_schema import AssessmentOutput
from langchain_core.messages import AIMessage

# Sample GraphState with completed investigations for reporting
SAMPLE_GRAPH_STATE_FOR_REPORTING = GraphState(
    user_query="Check device health",
    investigations=[
        Investigation(
            device_name="xrd-1",
            device_profile="PE router profile",
            role="PE",
            objective="Check device health",
            working_plan_steps="Step 1: Check system info",
            execution_results=[],
            status=InvestigationStatus.COMPLETED,
            priority=InvestigationPriority.HIGH,
            dependencies=[],
            report="Device xrd-1 is healthy",
            error_details=None,
        ),
        Investigation(
            device_name="xrd-2",
            device_profile="P router profile",
            role="P",
            objective="Check device health",
            working_plan_steps="Step 1: Check system info",
            execution_results=[],
            status=InvestigationStatus.FAILED,
            priority=InvestigationPriority.MEDIUM,
            dependencies=[],
            report=None,
            error_details="Connection timeout",
        ),
    ],
    historical_context=[
        HistoricalContext(
            session_id="session-1",
            previous_report="Previous investigation report",
            learned_patterns="Pattern 1: Network issues",
            device_relationships="xrd-1 -> xrd-2",
        )
    ],
    max_retries=3,
    current_retries=1,
    assessment=AssessmentOutput(
        is_objective_achieved=True,
        notes_for_final_report="Investigation completed successfully",
        feedback_for_retry=None,
    ),
    final_report=None,
)

# Sample GraphState with no investigations
EMPTY_GRAPH_STATE_FOR_REPORTING = GraphState(
    user_query="test query",
    investigations=[],
    historical_context=[],
    max_retries=3,
    current_retries=0,
    assessment=None,
    final_report=None,
)

# Sample historical contexts for testing
SAMPLE_HISTORICAL_CONTEXTS = [
    HistoricalContext(
        session_id="session-1",
        previous_report="Report from session 1",
        learned_patterns="Pattern 1: Test pattern",
        device_relationships="device1 -> device2",
    ),
    HistoricalContext(
        session_id="session-2",
        previous_report="Report from session 2",
        learned_patterns="Pattern 2: Another pattern",
        device_relationships="device2 -> device3",
    ),
]


# Sample AIMessage response for testing
SAMPLE_AI_RESPONSE = AIMessage(
    content="Generated report content",
    id="test-response",
)

# Sample AIMessage with list content
SAMPLE_AI_RESPONSE_LIST = AIMessage(
    content=["Part 1 of report", "Part 2 of report"],
    id="test-response-list",
)

# Sample final report
SAMPLE_FINAL_REPORT = "This is a generated final report"
