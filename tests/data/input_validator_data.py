"""
Test data for input_validator node tests.
Contains realistic data structures used in input_validator functions.
"""

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from schemas.state import GraphState, Investigation, InvestigationStatus
from src.nodes.input_validator.processing import InvestigationPlanningResponse

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

EMPTY_MCP_RESPONSE = {"messages": []}

INVALID_MCP_RESPONSE = {"not_messages": "invalid"}

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

SAMPLE_INVESTIGATION_PLANNING_RESPONSE = InvestigationPlanningResponse(
    device_names=["xrd-1", "xrd-2"]
)

EMPTY_INVESTIGATION_PLANNING_RESPONSE = InvestigationPlanningResponse(
    device_names=[]
)

SAMPLE_GRAPH_STATE = GraphState(
    messages=[HumanMessage(content="test query")],
    investigations=[],
)

SAMPLE_AI_MESSAGE = AIMessage(
    content="Device analysis complete: xrd-1 (PE), xrd-2 (PE)",
    id="test-ai-msg",
)

SAMPLE_AI_MESSAGE_LIST_CONTENT = AIMessage(
    content=["Part 1: Device analysis", "Part 2: Results"],
    id="test-ai-msg-list",
)
