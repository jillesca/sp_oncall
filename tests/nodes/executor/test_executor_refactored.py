"""
Tests for the refactored executor node functionality.

This module tests the enhanced extraction of LLM analysis and tool execution results
from MCP responses, ensuring proper handling of both AIMessage and ToolMessage types.
"""

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from src.nodes.executor import (
    _extract_response_content,
    _extract_last_ai_message,
    _extract_tool_messages,
    _convert_tool_message_to_executed_call,
    _process_llm_response,
)
from schemas.state import ExecutedToolCall
from tests.nodes.executor.mpc_response_data import mpc_response


class TestExtractResponseContent:
    """Test the main response content extraction function."""

    def test_extract_response_content_success(self):
        """Test successful extraction of LLM analysis and tool calls."""
        llm_analysis, executed_tool_calls = _extract_response_content(
            mpc_response
        )

        # Verify LLM analysis is extracted
        assert isinstance(llm_analysis, str)
        assert len(llm_analysis) > 0
        assert "general health check for device xrd-5" in llm_analysis

        # Verify tool calls are extracted
        assert isinstance(executed_tool_calls, list)
        assert len(executed_tool_calls) == 7  # Based on the sample data

        # Verify tool call functions
        expected_functions = [
            "get_system_info",
            "get_interface_info",
            "get_mpls_info",
            "get_routing_info",
            "get_vpn_info",
            "get_logs",
            "get_device_profile_api",
        ]

        actual_functions = [call.function for call in executed_tool_calls]
        assert actual_functions == expected_functions

    def test_extract_response_content_empty_messages(self):
        """Test handling of empty messages."""
        empty_response = {"messages": []}

        with pytest.raises(
            ValueError, match="No messages found in MCP response"
        ):
            _extract_response_content(empty_response)

    def test_extract_response_content_no_messages_key(self):
        """Test handling of response without messages key."""
        invalid_response = {"data": "some data"}

        with pytest.raises(
            ValueError, match="No messages found in MCP response"
        ):
            _extract_response_content(invalid_response)


class TestExtractLastAiMessage:
    """Test extraction of the last AIMessage."""

    def test_extract_last_ai_message_success(self):
        """Test successful extraction of the last AIMessage."""
        messages = mpc_response["messages"]
        content = _extract_last_ai_message(messages)

        assert isinstance(content, str)
        assert "general health check for device xrd-5" in content
        assert "Executive summary" in content

    def test_extract_last_ai_message_with_list_content(self):
        """Test handling of AIMessage with list content."""
        ai_msg_with_list = AIMessage(content=["Part 1", "Part 2", "Part 3"])
        messages = [ai_msg_with_list]

        content = _extract_last_ai_message(messages)
        assert content == "Part 1 Part 2 Part 3"

    def test_extract_last_ai_message_no_ai_messages(self):
        """Test handling when no AIMessage exists."""
        tool_msg = ToolMessage(
            content="test", name="test_tool", id="123", tool_call_id="call_123"
        )
        messages = [tool_msg]

        with pytest.raises(ValueError, match="No AIMessage found in messages"):
            _extract_last_ai_message(messages)

    def test_extract_last_ai_message_multiple_ai_messages(self):
        """Test that the last AIMessage is selected when multiple exist."""
        ai_msg_1 = AIMessage(content="First message")
        ai_msg_2 = AIMessage(content="Second message")
        ai_msg_3 = AIMessage(content="Last message")

        messages = [ai_msg_1, ai_msg_2, ai_msg_3]
        content = _extract_last_ai_message(messages)

        assert content == "Last message"


class TestExtractToolMessages:
    """Test extraction and conversion of ToolMessages."""

    def test_extract_tool_messages_success(self):
        """Test successful extraction of ToolMessages."""
        messages = mpc_response["messages"]
        executed_calls = _extract_tool_messages(messages)

        assert len(executed_calls) == 7
        assert all(
            isinstance(call, ExecutedToolCall) for call in executed_calls
        )

        # Check first tool call
        first_call = executed_calls[0]
        assert first_call.function == "get_system_info"
        assert isinstance(first_call.result, dict)
        assert first_call.result["device_name"] == "xrd-5"

    def test_extract_tool_messages_no_tool_messages(self):
        """Test handling when no ToolMessages exist."""
        ai_msg = AIMessage(content="Test message")
        messages = [ai_msg]

        executed_calls = _extract_tool_messages(messages)
        assert executed_calls == []

    def test_extract_tool_messages_with_conversion_error(self):
        """Test handling of ToolMessage conversion errors."""
        # Create a malformed ToolMessage that will cause conversion errors
        malformed_tool_msg = ToolMessage(
            content="invalid json {",
            name="test_function",
            id="123",
            tool_call_id="call_123",
        )

        executed_calls = _extract_tool_messages([malformed_tool_msg])

        assert len(executed_calls) == 1
        assert executed_calls[0].function == "test_function"
        # Should handle invalid JSON gracefully by creating raw_content
        assert executed_calls[0].result is not None
        assert "raw_content" in executed_calls[0].result


class TestConvertToolMessageToExecutedCall:
    """Test conversion of ToolMessage to ExecutedToolCall."""

    def test_convert_tool_message_success(self):
        """Test successful conversion of ToolMessage."""
        messages = mpc_response["messages"]
        tool_messages = [
            msg for msg in messages if isinstance(msg, ToolMessage)
        ]

        executed_call = _convert_tool_message_to_executed_call(
            tool_messages[0]
        )

        assert executed_call.function == "get_system_info"
        assert isinstance(executed_call.result, dict)
        assert executed_call.result["device_name"] == "xrd-5"
        assert executed_call.result["status"] == "success"
        assert "tool_call_id" in executed_call.params

    def test_convert_tool_message_with_list_content(self):
        """Test conversion with list content."""
        tool_msg = ToolMessage(
            content=["item1", "item2"],
            name="test_function",
            id="123",
            tool_call_id="call_123",
        )

        executed_call = _convert_tool_message_to_executed_call(tool_msg)

        assert executed_call.function == "test_function"
        assert executed_call.result is not None
        assert "raw_content" in executed_call.result
        assert executed_call.result["raw_content"] == "item1 item2"

    def test_convert_tool_message_invalid_json(self):
        """Test conversion with invalid JSON content."""
        tool_msg = ToolMessage(
            content="invalid json {",
            name="test_function",
            id="123",
            tool_call_id="call_123",
        )

        executed_call = _convert_tool_message_to_executed_call(tool_msg)

        assert executed_call.function == "test_function"
        assert executed_call.result is not None
        assert "raw_content" in executed_call.result
        assert executed_call.result["raw_content"] == "invalid json {"

    def test_convert_tool_message_no_name(self):
        """Test conversion when ToolMessage has no name."""
        tool_msg = ToolMessage(
            content='{"status": "success"}',
            name=None,
            id="123",
            tool_call_id="call_123",
        )

        executed_call = _convert_tool_message_to_executed_call(tool_msg)

        assert executed_call.function == "unknown"


class TestProcessLlmResponse:
    """Test processing of LLM response into StepExecutionResult."""

    def test_process_llm_response_success(self):
        """Test successful processing of LLM response."""
        llm_analysis = "This is a comprehensive analysis of device xrd-5."

        executed_tool_calls = [
            ExecutedToolCall(
                function="get_system_info",
                result={"status": "success", "device_name": "xrd-5"},
            ),
            ExecutedToolCall(
                function="get_interface_info",
                result={"status": "success", "device_name": "xrd-5"},
            ),
        ]

        result = _process_llm_response(llm_analysis, executed_tool_calls)

        assert result.investigation_report == llm_analysis
        assert result.executed_calls == executed_tool_calls

    def test_process_llm_response_with_limitations(self):
        """Test processing with tool calls that have errors."""
        llm_analysis = "Analysis with some limitations."

        executed_tool_calls = [
            ExecutedToolCall(
                function="get_bgp_info",
                error="BGP feature not available",
            ),
            ExecutedToolCall(
                function="get_routing_info",
                result={
                    "status": "partial_success",
                    "metadata": {"protocol_errors": {"bgp": "not found"}},
                },
            ),
        ]

        result = _process_llm_response(llm_analysis, executed_tool_calls)

        assert result.investigation_report == llm_analysis
        assert len(result.executed_calls) == 2
        assert result.executed_calls[0].error == "BGP feature not available"

    def test_process_llm_response_empty_calls(self):
        """Test processing with no tool calls."""
        llm_analysis = "Simple analysis without tool calls."
        executed_tool_calls = []

        result = _process_llm_response(llm_analysis, executed_tool_calls)

        assert result.investigation_report == llm_analysis
        assert result.executed_calls == []


class TestIntegration:
    """Integration tests using the actual MCP response data."""

    def test_full_extraction_workflow(self):
        """Test the complete extraction workflow with real data."""
        # Extract both LLM analysis and tool calls
        llm_analysis, executed_tool_calls = _extract_response_content(
            mpc_response
        )

        # Process into final result
        result = _process_llm_response(llm_analysis, executed_tool_calls)

        # Verify the complete result
        assert isinstance(result.investigation_report, str)
        assert (
            len(result.investigation_report) > 1000
        )  # Should be a substantial report
        assert len(result.executed_calls) == 7

        # Verify specific tool calls are present
        function_names = [call.function for call in result.executed_calls]
        assert "get_system_info" in function_names
        assert "get_interface_info" in function_names
        assert "get_routing_info" in function_names

        # Verify tool results contain expected data
        system_info_call = next(
            call
            for call in result.executed_calls
            if call.function == "get_system_info"
        )
        assert system_info_call.result is not None
        assert system_info_call.result["device_name"] == "xrd-5"
        assert system_info_call.result["status"] == "success"
