"""
Test data for input_validator node tests.
Contains realistic data structures used in input_validator functions.
"""

from schemas.state import (
    GraphState,
    Investigation,
    InvestigationStatus,
    InvestigationPriority,
)
from src.nodes.input_validator.processing import (
    DeviceToInvestigate,
    InvestigationPlanningResponse,
)
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# Sample MCP response for device extraction
SAMPLE_MCP_RESPONSE_FOR_EXTRACTION = {
    "messages": [
        HumanMessage(
            content="User query: how are my routers PE doing?",
            id="msg-1",
        ),
        AIMessage(
            content="I'll analyze your PE routers.",
            tool_calls=[
                {
                    "name": "get_devices",
                    "args": {},
                    "id": "call_123",
                    "type": "tool_call",
                }
            ],
            id="msg-2",
        ),
        ToolMessage(
            content='{"devices": [{"name": "xrd-1", "role": "PE"}, {"name": "xrd-2", "role": "PE"}]}',
            name="get_devices",
            tool_call_id="call_123",
            id="msg-3",
        ),
        AIMessage(
            content="PE Routers found: xrd-1, xrd-2",
            id="msg-4",
        ),
    ]
}

# Sample MCP response with no messages
EMPTY_MCP_RESPONSE = {"messages": []}

# Sample MCP response with invalid structure
INVALID_MCP_RESPONSE = {"not_messages": "invalid"}

# Sample MCP response with no AI messages
NO_AI_MESSAGE_RESPONSE = {
    "messages": [
        ToolMessage(
            content='{"devices": []}',
            name="get_devices",
            tool_call_id="call_123",
            id="msg-1",
        ),
    ]
}

# Sample investigation planning response
SAMPLE_INVESTIGATION_PLANNING_RESPONSE = InvestigationPlanningResponse(
    devices=[
        DeviceToInvestigate(
            device_name="xrd-1",
            device_profile="PE router with MPLS",
            role="PE",
        ),
        DeviceToInvestigate(
            device_name="xrd-2", device_profile="PE router with BGP", role="PE"
        ),
    ]
)

# Empty investigation planning response
EMPTY_INVESTIGATION_PLANNING_RESPONSE = InvestigationPlanningResponse(
    devices=[]
)

# Sample GraphState for building failed state
SAMPLE_GRAPH_STATE = GraphState(
    user_query="test query",
    investigations=[],
    workflow_session=[],
    max_retries=3,
    current_retries=0,
    assessment=None,
    final_report=None,
)

# Test data for device profile normalization
DEVICE_PROFILE_TEST_CASES = [
    # (input, expected_output, description)
    (None, "unknown", "None input"),
    ("", "unknown", "Empty string"),
    ("   ", "unknown", "Whitespace only"),
    ("simple_string", "simple_string", "Simple string"),
    ("  trimmed_string  ", "trimmed_string", "String with whitespace"),
    ({"key": "value"}, '{"key": "value"}', "Simple dict"),
    ({}, "unknown", "Empty dict"),
    (
        {"complex": {"nested": "value"}},
        '{"complex": {"nested": "value"}}',
        "Complex dict",
    ),
    (123, "123", "Integer"),
    (True, "True", "Boolean"),
    ([], "[]", "Empty list"),
]

# Sample AIMessage for extraction
SAMPLE_AI_MESSAGE = AIMessage(
    content="Device analysis complete: xrd-1 (PE), xrd-2 (PE)",
    id="test-ai-msg",
)

# Sample AIMessage with list content
SAMPLE_AI_MESSAGE_LIST_CONTENT = AIMessage(
    content=["Part 1: Device analysis", "Part 2: Results"],
    id="test-ai-msg-list",
)
