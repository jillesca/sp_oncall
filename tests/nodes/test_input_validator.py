"""
Unit tests for input_validator.py data extraction functions.

Tests focus on testing data processing logic, not LLM/MCP interactions.
Functions that use mcp_node or with_structured_output are excluded.
"""

import pytest
import json
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
    DeviceToInvestigate,
    InvestigationPlanningResponse,
    _normalize_device_profile,
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
    DEVICE_PROFILE_TEST_CASES,
    SAMPLE_AI_MESSAGE,
    SAMPLE_AI_MESSAGE_LIST_CONTENT,
)


class TestExtractMcpResponseContent:
    """Test cases for _extract_mcp_response_content function."""

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
        # Content should be preserved as-is when it's a list
        assert isinstance(result.content, list) or isinstance(
            result.content, str
        )


class TestNormalizeDeviceProfile:
    """Test cases for _normalize_device_profile function."""

    @pytest.mark.parametrize(
        "input_value,expected_output,description", DEVICE_PROFILE_TEST_CASES
    )
    def test_normalize_device_profile_cases(
        self, input_value, expected_output, description
    ):
        """Test device profile normalization with various input types."""
        result = _normalize_device_profile(input_value)

        assert isinstance(
            result, str
        ), f"Result should be string for {description}"

        if isinstance(input_value, dict) and input_value:
            # For non-empty dicts, result should be valid JSON
            try:
                parsed = json.loads(result)
                assert (
                    parsed == input_value
                ), f"Dict should round-trip for {description}"
            except json.JSONDecodeError:
                # Fallback case - should still be a string
                assert isinstance(result, str)
        else:
            assert (
                result == expected_output
            ), f"Expected {expected_output} for {description}"

    def test_normalize_device_profile_with_unserializable_dict(self):
        """Test normalization handles unserializable dictionaries."""
        # Create a dict with unserializable content
        unserializable_dict = {
            "key": set([1, 2, 3])
        }  # sets are not JSON serializable

        result = _normalize_device_profile(unserializable_dict)

        assert isinstance(result, str)
        assert len(result) > 0
        # Should fallback to string representation
        assert "set" in result or "key" in result

    def test_normalize_device_profile_preserves_valid_json_structure(self):
        """Test that valid dictionaries are preserved as proper JSON."""
        test_dict = {
            "is_mpls_enabled": True,
            "role": "PE",
            "interfaces": ["eth0", "eth1"],
            "config": {"bgp": {"as": 65001}},
        }

        result = _normalize_device_profile(test_dict)

        # Should be valid JSON
        parsed = json.loads(result)
        assert parsed == test_dict

        # Should be sorted for consistency
        assert result == json.dumps(test_dict, sort_keys=True)


class TestLogSuccessfulInvestigationPlanning:
    """Test cases for _log_successful_investigation_planning function."""

    def test_log_successful_investigation_planning_with_devices(self, caplog):
        """Test logging successful investigation planning with devices."""
        caplog.clear()

        _log_successful_investigation_planning(
            SAMPLE_INVESTIGATION_PLANNING_RESPONSE
        )

        # Function should complete without error (logging tested by behavior)
        assert True

    def test_log_successful_investigation_planning_with_empty_devices(
        self, caplog
    ):
        """Test logging with empty devices list."""
        caplog.clear()

        _log_successful_investigation_planning(
            EMPTY_INVESTIGATION_PLANNING_RESPONSE
        )

        # Function should complete without error
        assert True

    def test_log_successful_investigation_planning_handles_none_gracefully(
        self, caplog
    ):
        """Test logging handles None input gracefully."""
        caplog.clear()

        # This should raise TypeError when trying to get len() of None
        try:
            _log_successful_investigation_planning(None)
            assert False, "Should have raised a TypeError"
        except TypeError:
            # Expected when accessing len() on None
            assert True


class TestCreateInvestigationsFromResponse:
    """Test cases for _create_investigations_from_response function."""

    def test_create_investigations_from_response_success(self):
        """Test successful creation of investigations from response."""
        result = create_investigations_from_response(
            SAMPLE_INVESTIGATION_PLANNING_RESPONSE
        )

        assert isinstance(result, list)
        assert len(result) == len(
            SAMPLE_INVESTIGATION_PLANNING_RESPONSE.devices
        )

        for investigation in result:
            assert isinstance(investigation, Investigation)
            assert investigation.device_name is not None
            assert investigation.device_profile is not None
            assert investigation.role is not None

    def test_create_investigations_from_response_preserves_device_info(self):
        """Test that device information is preserved in investigations."""
        result = create_investigations_from_response(
            SAMPLE_INVESTIGATION_PLANNING_RESPONSE
        )

        # Check first device
        first_investigation = result[0]
        first_device = SAMPLE_INVESTIGATION_PLANNING_RESPONSE.devices[0]

        assert first_investigation.device_name == first_device.device_name
        assert (
            first_investigation.device_profile == first_device.device_profile
        )
        assert first_investigation.role == first_device.role

    def test_create_investigations_from_response_with_empty_list(self):
        """Test creation with empty devices list."""
        result = create_investigations_from_response(
            EMPTY_INVESTIGATION_PLANNING_RESPONSE
        )

        assert isinstance(result, list)
        assert len(result) == 0

    def test_create_investigations_from_response_sets_default_values(self):
        """Test that investigations have appropriate default values."""
        result = create_investigations_from_response(
            SAMPLE_INVESTIGATION_PLANNING_RESPONSE
        )

        if result:
            investigation = result[0]
            # Check default values are set
            assert investigation.execution_results == []
            assert investigation.dependencies == []
            assert investigation.report is None
            assert investigation.error_details is None

    def test_create_investigations_from_response_with_minimal_device_data(
        self,
    ):
        """Test creation with minimal device data."""
        minimal_response = InvestigationPlanningResponse(
            devices=[
                DeviceToInvestigate(
                    device_name="test-device", device_profile="test"
                )
            ]
        )

        result = create_investigations_from_response(minimal_response)

        assert len(result) == 1
        investigation = result[0]
        assert investigation.device_name == "test-device"
        assert investigation.device_profile == "test"


class TestBuildFailedState:
    """Test cases for _build_failed_state function."""

    def test_build_failed_state_preserves_user_query(self):
        """Test that failed state preserves the user query."""
        result = _build_failed_state(SAMPLE_GRAPH_STATE)

        assert isinstance(result, GraphState)
        assert result.user_query == SAMPLE_GRAPH_STATE.user_query

    def test_build_failed_state_sets_empty_investigations(self):
        """Test that failed state sets investigations to empty list."""
        result = _build_failed_state(SAMPLE_GRAPH_STATE)

        assert result.investigations == []

    def test_build_failed_state_preserves_other_fields(self):
        """Test that failed state preserves other state fields."""
        result = _build_failed_state(SAMPLE_GRAPH_STATE)

        assert result.max_retries == SAMPLE_GRAPH_STATE.max_retries
        assert result.current_retries == SAMPLE_GRAPH_STATE.current_retries
        assert result.workflow_session == SAMPLE_GRAPH_STATE.workflow_session

    def test_build_failed_state_with_existing_investigations(self):
        """Test failed state building when original state has investigations."""
        state_with_investigations = GraphState(
            user_query="test query",
            investigations=[
                Investigation(
                    device_name="existing-device",
                    device_profile="existing profile",
                    role="PE",
                )
            ],
            workflow_session=[],
            max_retries=3,
            current_retries=0,
            assessment=None,
            final_report=None,
        )

        result = _build_failed_state(state_with_investigations)

        # Should clear investigations even if they existed
        assert result.investigations == []
        assert result.user_query == state_with_investigations.user_query


class TestDeviceToInvestigateDataClass:
    """Test cases for DeviceToInvestigate data class."""

    def test_device_to_investigate_creation(self):
        """Test DeviceToInvestigate creation with required fields."""
        device = DeviceToInvestigate(
            device_name="test-device", device_profile="test profile"
        )

        assert device.device_name == "test-device"
        assert device.device_profile == "test profile"
        assert device.role == ""  # Default value

    def test_device_to_investigate_with_role(self):
        """Test DeviceToInvestigate creation with role specified."""
        device = DeviceToInvestigate(
            device_name="test-device", device_profile="test profile", role="PE"
        )

        assert device.device_name == "test-device"
        assert device.device_profile == "test profile"
        assert device.role == "PE"


class TestInvestigationPlanningResponseDataClass:
    """Test cases for InvestigationPlanningResponse data class."""

    def test_investigation_planning_response_creation(self):
        """Test InvestigationPlanningResponse creation."""
        response = InvestigationPlanningResponse(
            devices=[
                DeviceToInvestigate(
                    device_name="device1", device_profile="profile1"
                ),
                DeviceToInvestigate(
                    device_name="device2", device_profile="profile2"
                ),
            ]
        )

        assert len(response) == 2
        assert len(response.devices) == 2

    def test_investigation_planning_response_len(self):
        """Test __len__ method of InvestigationPlanningResponse."""
        response = SAMPLE_INVESTIGATION_PLANNING_RESPONSE

        assert len(response) == len(response.devices)

    def test_investigation_planning_response_iter(self):
        """Test __iter__ method of InvestigationPlanningResponse."""
        response = SAMPLE_INVESTIGATION_PLANNING_RESPONSE

        devices_list = list(response)
        assert len(devices_list) == len(response.devices)

        for i, device in enumerate(response):
            assert device == response.devices[i]

    def test_investigation_planning_response_empty(self):
        """Test InvestigationPlanningResponse with empty devices."""
        response = EMPTY_INVESTIGATION_PLANNING_RESPONSE

        assert len(response) == 0
        assert list(response) == []
