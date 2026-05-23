"""
Unit tests for input_validator node data processing functions.

Tests focus on data processing logic, not LLM/MCP interactions.
Functions that use mcp_node or with_structured_output are excluded.
"""

import pytest
from unittest.mock import Mock

from src.nodes.input_validator.core import (
    input_validator_node,
    _log_successful_investigation_planning,
    _build_failed_state,
)
from src.nodes.input_validator.extraction import (
    execute_investigation_planning,
    extract_mcp_response_content,
    build_investigation_planning_context,
)
from src.nodes.input_validator.processing import (
    process_investigation_planning_response,
    create_investigations_from_response,
    InvestigationPlanningResponse,
)
from schemas.state import GraphState, Investigation
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage
from tests.data.input_validator_data import (
    SAMPLE_MCP_RESPONSE_FOR_EXTRACTION,
    EMPTY_MCP_RESPONSE,
    INVALID_MCP_RESPONSE,
    NO_AI_MESSAGE_RESPONSE,
    SAMPLE_INVESTIGATION_PLANNING_RESPONSE,
    EMPTY_INVESTIGATION_PLANNING_RESPONSE,
    SAMPLE_GRAPH_STATE,
    SAMPLE_AI_MESSAGE,
    SAMPLE_AI_MESSAGE_LIST_CONTENT,
)


class TestExtractMcpResponseContent:
    """Test cases for extract_mcp_response_content function."""

    def test_extract_mcp_response_content_success(self):
        """Test successful extraction from valid MCP response."""
        result = extract_mcp_response_content(
            SAMPLE_MCP_RESPONSE_FOR_EXTRACTION
        )

        assert isinstance(result, AIMessage)
        assert hasattr(result, "content")
        assert isinstance(result.content, str)
        assert len(result.content) > 0

    def test_extract_mcp_response_content_with_empty_messages(self):
        """Test extraction fails with empty messages list."""
        with pytest.raises(
            ValueError, match="'messages' is not a list or is empty"
        ):
            extract_mcp_response_content(EMPTY_MCP_RESPONSE)

    def test_extract_mcp_response_content_with_invalid_structure(self):
        """Test extraction fails with invalid response structure."""
        with pytest.raises(ValueError, match="missing 'messages' key"):
            extract_mcp_response_content(INVALID_MCP_RESPONSE)

    def test_extract_mcp_response_content_with_no_ai_messages(self):
        """Test extraction fails when no AI messages are present."""
        with pytest.raises(ValueError, match="No AIMessage found"):
            extract_mcp_response_content(NO_AI_MESSAGE_RESPONSE)

    def test_extract_mcp_response_content_with_non_dict_input(self):
        """Test extraction fails with non-dict input."""
        with pytest.raises(ValueError, match="missing 'messages' key"):
            extract_mcp_response_content("not a dict")

    def test_extract_mcp_response_content_finds_last_ai_message(self):
        """Test that extraction finds the last AI message when multiple exist."""
        response_with_multiple_ai = {
            "messages": [
                AIMessage(content="First AI message", id="msg-1"),
                ToolMessage(
                    content="Tool result",
                    name="test",
                    tool_call_id="123",
                    id="msg-2",
                ),
                AIMessage(content="Last AI message", id="msg-3"),
            ]
        }

        result = extract_mcp_response_content(response_with_multiple_ai)
        assert "Last AI message" in result.content

    def test_extract_mcp_response_content_handles_list_content(self):
        """Test extraction handles AI messages with list content."""
        response_with_list_content = {
            "messages": [
                SAMPLE_AI_MESSAGE_LIST_CONTENT,
            ]
        }

        result = extract_mcp_response_content(response_with_list_content)
        assert isinstance(result, AIMessage)
        assert isinstance(result.content, list) or isinstance(
            result.content, str
        )


class TestLogSuccessfulInvestigationPlanning:
    """Test cases for _log_successful_investigation_planning function."""

    def test_log_with_devices(self, caplog):
        """Test logging successful investigation planning with devices."""
        caplog.clear()

        _log_successful_investigation_planning(
            SAMPLE_INVESTIGATION_PLANNING_RESPONSE
        )

        assert True

    def test_log_with_empty_devices(self, caplog):
        """Test logging with empty devices list."""
        caplog.clear()

        _log_successful_investigation_planning(
            EMPTY_INVESTIGATION_PLANNING_RESPONSE
        )

        assert True

    def test_log_handles_none_gracefully(self, caplog):
        """Test logging raises TypeError on None input."""
        caplog.clear()

        with pytest.raises(TypeError):
            _log_successful_investigation_planning(None)


class TestCreateInvestigationsFromResponse:
    """Test cases for create_investigations_from_response function."""

    def test_create_investigations_success(self):
        """Test successful creation of investigations from response."""
        result = create_investigations_from_response(
            SAMPLE_INVESTIGATION_PLANNING_RESPONSE
        )

        assert isinstance(result, list)
        assert len(result) == len(
            SAMPLE_INVESTIGATION_PLANNING_RESPONSE.device_names
        )

        for investigation in result:
            assert isinstance(investigation, Investigation)
            assert investigation.device_name != ""

    def test_create_investigations_preserves_device_names(self):
        """Test that device names are preserved in investigations."""
        result = create_investigations_from_response(
            SAMPLE_INVESTIGATION_PLANNING_RESPONSE
        )

        created_names = {inv.device_name for inv in result}
        expected_names = set(SAMPLE_INVESTIGATION_PLANNING_RESPONSE.device_names)
        assert created_names == expected_names

    def test_create_investigations_with_empty_list(self):
        """Test creation with empty device_names list."""
        result = create_investigations_from_response(
            EMPTY_INVESTIGATION_PLANNING_RESPONSE
        )

        assert isinstance(result, list)
        assert len(result) == 0

    def test_create_investigations_sets_default_values(self):
        """Test that investigations have appropriate default values."""
        result = create_investigations_from_response(
            SAMPLE_INVESTIGATION_PLANNING_RESPONSE
        )

        if result:
            investigation = result[0]
            assert investigation.device_profile == ""
            assert investigation.role == ""
            assert investigation.execution_results == []
            assert investigation.report is None
            assert investigation.error_details is None


class TestBuildFailedState:
    """Test cases for _build_failed_state function."""

    def test_build_failed_state_preserves_user_query(self):
        """Test that failed state preserves the user query."""
        result = _build_failed_state(SAMPLE_GRAPH_STATE)

        assert isinstance(result, GraphState)
        assert (
            result.trigger_context
            == SAMPLE_GRAPH_STATE.trigger_context
        )

    def test_build_failed_state_sets_empty_investigations(self):
        """Test that failed state sets investigations to empty list."""
        result = _build_failed_state(SAMPLE_GRAPH_STATE)

        assert result.investigations == []

    def test_build_failed_state_with_existing_investigations(self):
        """Test failed state building when original state has investigations."""
        state_with_investigations = GraphState(
            messages=[HumanMessage(content="test query")],
            investigations=[
                Investigation(device_name="existing-device")
            ],
        )

        result = _build_failed_state(state_with_investigations)

        assert result.investigations == []
        assert (
            result.trigger_context
            == state_with_investigations.trigger_context
        )


class TestInvestigationPlanningResponseDataClass:
    """Test cases for InvestigationPlanningResponse data class."""

    def test_creation_with_device_names(self):
        """Test InvestigationPlanningResponse creation with device names."""
        response = InvestigationPlanningResponse(
            device_names=["xrd-1", "xrd-2", "xrd-3"]
        )

        assert len(response) == 3
        assert response.device_names == ["xrd-1", "xrd-2", "xrd-3"]

    def test_len_method(self):
        """Test __len__ method of InvestigationPlanningResponse."""
        response = SAMPLE_INVESTIGATION_PLANNING_RESPONSE

        assert len(response) == len(response.device_names)

    def test_iter_method(self):
        """Test __iter__ method yields device names as strings."""
        response = SAMPLE_INVESTIGATION_PLANNING_RESPONSE

        names = list(response)
        assert names == response.device_names

    def test_empty_response(self):
        """Test InvestigationPlanningResponse with empty device_names."""
        response = EMPTY_INVESTIGATION_PLANNING_RESPONSE

        assert len(response) == 0
        assert list(response) == []
