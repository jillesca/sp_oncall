"""
Test data for executor node tests.
Contains realistic data structures used in executor functions.
"""

from schemas.state import (
    GraphState,
    Investigation,
    InvestigationStatus,
    InvestigationPriority,
    ExecutedToolCall,
)
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# Sample GraphState with ready investigations
SAMPLE_GRAPH_STATE_WITH_READY_INVESTIGATIONS = GraphState(
    user_query="Check device health",
    investigations=[
        Investigation(
            device_name="xrd-1",
            device_profile="PE router profile",
            role="PE",
            objective="Check device health",
            working_plan_steps="Step 1: Check system info",
            execution_results=[],
            status=InvestigationStatus.PENDING,
            priority=InvestigationPriority.HIGH,
            dependencies=[],
            report=None,
            error_details=None,
        ),
        Investigation(
            device_name="xrd-2",
            device_profile="P router profile",
            role="P",
            objective="Check device health",
            working_plan_steps="Step 1: Check system info",
            execution_results=[],
            status=InvestigationStatus.COMPLETED,  # This one is not ready
            priority=InvestigationPriority.MEDIUM,
            dependencies=[],
            report="Already completed",
            error_details=None,
        ),
    ],
    workflow_session=[],
    max_retries=3,
    current_retries=0,
    assessment=None,
    final_report=None,
)

# Sample MCP response with messages
SAMPLE_MCP_RESPONSE = {
    "messages": [
        HumanMessage(
            content="Check device xrd-1 health",
            id="msg-1",
        ),
        AIMessage(
            content="I'll check the device health now.",
            tool_calls=[
                {
                    "name": "get_system_info",
                    "args": {"device_name": "xrd-1"},
                    "id": "call_123",
                    "type": "tool_call",
                }
            ],
            id="msg-2",
        ),
        ToolMessage(
            content='{"status": "success", "data": {"hostname": "xrd-1", "uptime": "30 days"}}',
            name="get_system_info",
            tool_call_id="call_123",
            id="msg-3",
        ),
        AIMessage(
            content="The device xrd-1 is healthy with 30 days uptime.",
            id="msg-4",
        ),
    ]
}

# Sample MCP response with no messages
EMPTY_MCP_RESPONSE = {"messages": []}

# Sample MCP response with invalid structure
INVALID_MCP_RESPONSE = {"not_messages": "invalid"}

# Sample ExecutedToolCall objects
SAMPLE_EXECUTED_TOOL_CALLS = [
    ExecutedToolCall(
        function="get_system_info",
        params={"device_name": "xrd-1"},
        result={"status": "success", "data": {"hostname": "xrd-1"}},
        error=None,
    ),
    ExecutedToolCall(
        function="get_interface_status",
        params={"device_name": "xrd-1"},
        result={"status": "success", "interfaces": ["eth0", "eth1"]},
        error=None,
    ),
]

# Sample investigation for context building
SAMPLE_INVESTIGATION = Investigation(
    device_name="test-device",
    device_profile="test profile",
    role="PE",
    objective="Test objective",
    working_plan_steps="Test steps",
    execution_results=[],
    status=InvestigationStatus.PENDING,
    priority=InvestigationPriority.MEDIUM,
    dependencies=[],
    report=None,
    error_details=None,
)

# Sample updated investigations list
SAMPLE_UPDATED_INVESTIGATIONS = [
    Investigation(
        device_name="xrd-1",
        device_profile="PE router profile",
        role="PE",
        objective="Check device health",
        working_plan_steps="Step 1: Check system info",
        execution_results=SAMPLE_EXECUTED_TOOL_CALLS,
        status=InvestigationStatus.COMPLETED,
        priority=InvestigationPriority.HIGH,
        dependencies=[],
        report="Investigation completed successfully",
        error_details=None,
    ),
]
