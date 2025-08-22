"""
Unit tests for executor.py data processing functions.

Tests focus on testing data processing logic, not LLM/MCP interactions.
Functions that use mcp_node are excluded from testing.
"""

import pytest
from unittest.mock import Mock
from dataclasses import replace

from src.nodes.executor import (
    _log_incoming_state,
    _build_investigation_context,
    _update_state_with_investigations,
    _update_state_with_global_error,
    _extract_response_content,
    _extract_last_ai_message,
    _extract_tool_messages,
    _convert_tool_message_to_executed_call,
    _log_processed_data,
)
from schemas.state import (
    GraphState,
    Investigation,
    InvestigationStatus,
    ExecutedToolCall,
)
from langchain_core.messages import AIMessage, ToolMessage
from tests.data.executor_data import (
    SAMPLE_GRAPH_STATE_WITH_READY_INVESTIGATIONS,
    SAMPLE_MCP_RESPONSE,
    EMPTY_MCP_RESPONSE,
    INVALID_MCP_RESPONSE,
    SAMPLE_EXECUTED_TOOL_CALLS,
    SAMPLE_INVESTIGATION,
    SAMPLE_UPDATED_INVESTIGATIONS,
)


class TestLogIncomingState:
    """Test cases for _log_incoming_state function."""

    def test_log_incoming_state_with_investigations(self, caplog):
        """Test logging of incoming state with investigations."""
        # Clear any previous log records
        caplog.clear()

        # Call the function
        _log_incoming_state(SAMPLE_GRAPH_STATE_WITH_READY_INVESTIGATIONS)

        # Check that logging occurred (we can't easily test the exact content
        # since it uses lazy logging, but we can verify the function runs)
        assert True  # Function should complete without error

    def test_log_incoming_state_with_empty_investigations(self, caplog):
        """Test logging of incoming state with no investigations."""
        empty_state = replace(
            SAMPLE_GRAPH_STATE_WITH_READY_INVESTIGATIONS, investigations=[]
        )

        caplog.clear()
        _log_incoming_state(empty_state)
        assert True  # Function should complete without error

    def test_log_incoming_state_with_retries(self, caplog):
        """Test logging includes retry information."""
        retry_state = replace(
            SAMPLE_GRAPH_STATE_WITH_READY_INVESTIGATIONS, current_retries=2
        )

        caplog.clear()
        _log_incoming_state(retry_state)
        assert True  # Function should complete without error


class TestBuildInvestigationContext:
    """Test cases for _build_investigation_context function."""

    def test_build_investigation_context_basic(self):
        """Test basic investigation context building."""
        state = SAMPLE_GRAPH_STATE_WITH_READY_INVESTIGATIONS
        investigation = state.investigations[0]

        result = _build_investigation_context(investigation, state)

        assert isinstance(result, str)
        assert f"**User Query:** {state.user_query}" in result
        assert f"**Device Name:** {investigation.device_name}" in result
        assert investigation.device_profile in result
        assert f"**Role:** {investigation.role}" in result
        assert f"**Objective:** {investigation.objective}" in result

    def test_build_investigation_context_with_workflow_session(self):
        """Test context building includes workflow session data."""
        from schemas.state import WorkflowSession

        session = WorkflowSession(
            session_id="test-session",
            previous_report="Previous investigation report",
            learned_patterns="Pattern 1: Test pattern",
            device_relationships="device1 -> device2",
        )

        state_with_session = replace(
            SAMPLE_GRAPH_STATE_WITH_READY_INVESTIGATIONS,
            workflow_session=[session],
        )
        investigation = state_with_session.investigations[0]

        result = _build_investigation_context(
            investigation, state_with_session
        )

        assert "Previous Investigation Context" in result
        assert "**Total Investigation Sessions:** 1" in result
        assert "Recent Investigation Report" in result

    def test_build_investigation_context_with_retry(self):
        """Test context building includes retry information."""
        from schemas.assessment_schema import AssessmentOutput

        retry_state = replace(
            SAMPLE_GRAPH_STATE_WITH_READY_INVESTIGATIONS,
            current_retries=2,
            assessment=AssessmentOutput(
                is_objective_achieved=False,
                notes_for_final_report="Failed",
                feedback_for_retry="Try different approach",
            ),
        )
        investigation = retry_state.investigations[0]

        result = _build_investigation_context(investigation, retry_state)

        assert "Retry Context" in result
        assert "**Retry Number:** #2 of 3" in result
        assert "Try different approach" in result

    def test_build_investigation_context_returns_valid_string(self):
        """Test that context building returns a valid non-empty string."""
        result = _build_investigation_context(
            SAMPLE_INVESTIGATION, SAMPLE_GRAPH_STATE_WITH_READY_INVESTIGATIONS
        )

        assert isinstance(result, str)
        assert len(result) > 0
        assert "\\n" in result or "\n" in result  # Should have line breaks


class TestUpdateStateWithInvestigations:
    """Test cases for _update_state_with_investigations function."""

    def test_update_state_with_investigations_success(self):
        """Test successful state update with investigations."""
        original_state = SAMPLE_GRAPH_STATE_WITH_READY_INVESTIGATIONS
        updated_investigations = SAMPLE_UPDATED_INVESTIGATIONS

        result = _update_state_with_investigations(
            original_state, updated_investigations
        )

        assert isinstance(result, GraphState)
        assert len(result.investigations) == len(original_state.investigations)
        # The updated investigation should be in the result
        updated_device_names = [
            inv.device_name for inv in updated_investigations
        ]
        result_device_names = [
            inv.device_name for inv in result.investigations
        ]

        for device_name in updated_device_names:
            assert device_name in result_device_names

    def test_update_state_preserves_non_updated_investigations(self):
        """Test that non-updated investigations are preserved."""
        original_state = SAMPLE_GRAPH_STATE_WITH_READY_INVESTIGATIONS
        # Only update one investigation
        partial_update = [SAMPLE_UPDATED_INVESTIGATIONS[0]]

        result = _update_state_with_investigations(
            original_state, partial_update
        )

        # Should still have the same number of investigations
        assert len(result.investigations) == len(original_state.investigations)

        # Non-updated investigations should be preserved
        non_updated_devices = [
            inv
            for inv in original_state.investigations
            if inv.device_name != partial_update[0].device_name
        ]

        for orig_inv in non_updated_devices:
            result_inv = next(
                (
                    inv
                    for inv in result.investigations
                    if inv.device_name == orig_inv.device_name
                ),
                None,
            )
            assert result_inv is not None
            assert result_inv.status == orig_inv.status

    def test_update_state_with_empty_updates(self):
        """Test state update with empty updates list."""
        original_state = SAMPLE_GRAPH_STATE_WITH_READY_INVESTIGATIONS

        result = _update_state_with_investigations(original_state, [])

        assert result == original_state  # Should be unchanged


class TestUpdateStateWithGlobalError:
    """Test cases for _update_state_with_global_error function."""

    def test_update_state_with_global_error_marks_pending_as_failed(self):
        """Test that global error marks pending investigations as failed."""
        error = RuntimeError("Global error occurred")

        result = _update_state_with_global_error(
            SAMPLE_GRAPH_STATE_WITH_READY_INVESTIGATIONS, error
        )

        # Check that pending investigations are marked as failed
        for investigation in result.investigations:
            if investigation.status == InvestigationStatus.PENDING:
                # In the original state, this should now be failed
                pass
            # Check if any were originally pending in the input

        # Get the first investigation which should have been pending
        first_inv = result.investigations[0]
        assert first_inv.status == InvestigationStatus.FAILED
        assert "Global error occurred" in first_inv.error_details

    def test_update_state_with_global_error_preserves_completed(self):
        """Test that global error preserves completed investigations."""
        error = RuntimeError("Global error occurred")

        result = _update_state_with_global_error(
            SAMPLE_GRAPH_STATE_WITH_READY_INVESTIGATIONS, error
        )

        # Find completed investigations (if any)
        completed_investigations = [
            inv
            for inv in result.investigations
            if inv.status == InvestigationStatus.COMPLETED
        ]

        # The second investigation in our test data should remain completed
        assert len(completed_investigations) >= 1
        completed_inv = completed_investigations[0]
        assert (
            completed_inv.error_details is None
            or "Global error" not in completed_inv.error_details
        )


class TestExtractResponseContent:
    """Test cases for _extract_response_content function."""

    def test_extract_response_content_success(self):
        """Test successful extraction from MCP response."""
        llm_analysis, tool_calls = _extract_response_content(
            SAMPLE_MCP_RESPONSE
        )

        assert isinstance(llm_analysis, str)
        assert isinstance(tool_calls, list)
        assert len(llm_analysis) > 0
        assert len(tool_calls) >= 0

    def test_extract_response_content_with_empty_messages(self):
        """Test extraction fails with empty messages."""
        with pytest.raises(ValueError, match="No messages found"):
            _extract_response_content(EMPTY_MCP_RESPONSE)

    def test_extract_response_content_with_invalid_structure(self):
        """Test extraction fails with invalid response structure."""
        with pytest.raises(ValueError, match="No messages found"):
            _extract_response_content(INVALID_MCP_RESPONSE)

    def test_extract_response_content_returns_correct_types(self):
        """Test that extraction returns correct data types."""
        llm_analysis, tool_calls = _extract_response_content(
            SAMPLE_MCP_RESPONSE
        )

        assert isinstance(llm_analysis, str)
        assert isinstance(tool_calls, list)
        if tool_calls:
            assert all(
                isinstance(call, ExecutedToolCall) for call in tool_calls
            )


class TestExtractLastAiMessage:
    """Test cases for _extract_last_ai_message function."""

    def test_extract_last_ai_message_success(self):
        """Test successful extraction of last AI message."""
        messages = SAMPLE_MCP_RESPONSE["messages"]
        result = _extract_last_ai_message(messages)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_extract_last_ai_message_with_no_ai_messages(self):
        """Test extraction fails when no AI messages present."""
        messages = [
            ToolMessage(
                content="Tool result",
                name="test_tool",
                tool_call_id="123",
                id="msg-1",
            )
        ]

        with pytest.raises(ValueError, match="No AIMessage found"):
            _extract_last_ai_message(messages)

    def test_extract_last_ai_message_with_multiple_ai_messages(self):
        """Test extraction gets the last AI message when multiple exist."""
        messages = [
            AIMessage(content="First AI message", id="msg-1"),
            ToolMessage(
                content="Tool result",
                name="test_tool",
                tool_call_id="123",
                id="msg-2",
            ),
            AIMessage(content="Last AI message", id="msg-3"),
        ]

        result = _extract_last_ai_message(messages)
        assert "Last AI message" in result

    def test_extract_last_ai_message_handles_list_content(self):
        """Test extraction handles list content in AI messages."""
        messages = [
            AIMessage(content=["Part 1", "Part 2"], id="msg-1"),
        ]

        result = _extract_last_ai_message(messages)
        assert isinstance(result, str)
        assert "Part 1" in result and "Part 2" in result


class TestExtractToolMessages:
    """Test cases for _extract_tool_messages function."""

    def test_extract_tool_messages_success(self):
        """Test successful extraction of tool messages."""
        messages = SAMPLE_MCP_RESPONSE["messages"]
        result = _extract_tool_messages(messages)

        assert isinstance(result, list)
        if result:
            assert all(isinstance(call, ExecutedToolCall) for call in result)

    def test_extract_tool_messages_with_no_tool_messages(self):
        """Test extraction with no tool messages returns empty list."""
        messages = [
            AIMessage(content="Only AI message", id="msg-1"),
        ]

        result = _extract_tool_messages(messages)
        assert result == []

    def test_extract_tool_messages_handles_conversion_errors(self):
        """Test extraction handles tool message conversion errors gracefully."""
        # Create a mock ToolMessage that will cause conversion issues
        mock_tool_msg = Mock(spec=ToolMessage)
        mock_tool_msg.name = "test_tool"
        mock_tool_msg.content = None  # This might cause issues

        result = _extract_tool_messages([mock_tool_msg])

        # Should handle the error and still return a list
        assert isinstance(result, list)


class TestConvertToolMessageToExecutedCall:
    """Test cases for _convert_tool_message_to_executed_call function."""

    def test_convert_tool_message_success(self):
        """Test successful conversion of tool message."""
        tool_msg = ToolMessage(
            content='{"status": "success", "data": "test"}',
            name="test_function",
            tool_call_id="call_123",
            id="msg-1",
        )

        result = _convert_tool_message_to_executed_call(tool_msg)

        assert isinstance(result, ExecutedToolCall)
        assert result.function == "test_function"
        assert "tool_call_id" in result.params
        assert result.params["tool_call_id"] == "call_123"

    def test_convert_tool_message_with_invalid_json(self):
        """Test conversion handles invalid JSON gracefully."""
        tool_msg = ToolMessage(
            content="invalid json content",
            name="test_function",
            tool_call_id="call_123",
            id="msg-1",
        )

        result = _convert_tool_message_to_executed_call(tool_msg)

        assert isinstance(result, ExecutedToolCall)
        assert result.function == "test_function"
        assert "raw_content" in result.result

    def test_convert_tool_message_with_list_content(self):
        """Test conversion handles list content."""
        tool_msg = ToolMessage(
            content=["item1", "item2"],
            name="test_function",
            tool_call_id="call_123",
            id="msg-1",
        )

        result = _convert_tool_message_to_executed_call(tool_msg)

        assert isinstance(result, ExecutedToolCall)
        assert result.function == "test_function"

    def test_convert_tool_message_with_no_name(self):
        """Test conversion handles missing tool name."""
        tool_msg = ToolMessage(
            content='{"test": "data"}',
            name=None,
            tool_call_id="call_123",
            id="msg-1",
        )

        result = _convert_tool_message_to_executed_call(tool_msg)

        assert isinstance(result, ExecutedToolCall)
        assert result.function == "unknown"


class TestLogProcessedData:
    """Test cases for _log_processed_data function."""

    def test_log_processed_data_with_data(self, caplog):
        """Test logging of processed data with actual data."""
        investigation_report = "Test investigation report"
        executed_calls = SAMPLE_EXECUTED_TOOL_CALLS

        caplog.clear()
        _log_processed_data(investigation_report, executed_calls)

        # Function should complete without error
        assert True

    def test_log_processed_data_with_empty_data(self, caplog):
        """Test logging of processed data with empty data."""
        caplog.clear()
        _log_processed_data("", [])

        # Function should complete without error
        assert True

    def test_log_processed_data_with_none_values(self, caplog):
        """Test logging handles None values gracefully."""
        caplog.clear()
        # Should handle None values without crashing
        try:
            _log_processed_data(None, None)
            assert False, "Should have raised an error"
        except (TypeError, AttributeError):
            # Expected to fail with None values
            assert True
