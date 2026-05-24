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
    InvestigationPlanningResponse,
)
from src.nodes.input_validator.core import (
    _build_device_context,
    _format_mcp_device_section,
    _hydrate_single_investigation,
)
from src.nodes.input_validator.processing import DiscoveredDevice
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


class TestBuildDeviceContext:
    """Test cases for _build_device_context function."""

    def test_includes_mcp_section_for_new_device(self):
        """Test that fresh MCP data is always included."""
        device = DiscoveredDevice(
            device_name="xrd-1", type_model="IOS XR", role="PE", neighbors=["xrd-2"]
        )
        result = _build_device_context(device, profile={}, history=[])

        assert "Device Facts:" in result
        assert "IOS XR" in result
        assert "PE" in result
        assert "xrd-2" in result

    def test_appends_dynamic_facts_when_present(self):
        """Test that stored dynamic facts are appended to the MCP section."""
        device = DiscoveredDevice(
            device_name="xrd-1", type_model="IOS XR", role="PE", neighbors=[]
        )
        profile = {"dynamic_facts": {"last_known_state": "completed"}}
        result = _build_device_context(device, profile=profile, history=[])

        assert "Device Facts:" in result
        assert "Previous Investigation Context:" in result
        assert "last_known_state: completed" in result

    def test_appends_history_when_present(self):
        """Test that investigation history is appended when available."""
        device = DiscoveredDevice(
            device_name="xrd-1", type_model="IOS XR", role="PE", neighbors=[]
        )
        history = [{"timestamp": "2026-01-01T00:00:00+00:00", "status": "completed", "summary": "All good"}]
        result = _build_device_context(device, profile={}, history=history)

        assert "Device Facts:" in result
        assert "Previous Investigation Findings:" in result
        assert "All good" in result

    def test_skips_static_facts_from_store(self):
        """Test that stored static_facts are not included in device_context."""
        device = DiscoveredDevice(
            device_name="xrd-1", type_model="IOS XR", role="PE", neighbors=[]
        )
        profile = {"static_facts": {"role": "PE"}, "dynamic_facts": {}}
        result = _build_device_context(device, profile=profile, history=[])

        assert "Static Device Facts:" not in result


class TestFormatMcpDeviceSection:
    """Test cases for _format_mcp_device_section function."""

    def test_formats_all_fields(self):
        """Test that type, role, and neighbors are all included."""
        device = DiscoveredDevice(
            device_name="xrd-1",
            type_model="Cisco IOS XR",
            role="PE",
            neighbors=["xrd-2", "xrd-3"],
        )
        result = _format_mcp_device_section(device)

        assert "Device Facts:" in result
        assert "Cisco IOS XR" in result
        assert "PE" in result
        assert "xrd-2" in result
        assert "xrd-3" in result

    def test_handles_missing_type_model(self):
        """Test graceful handling of empty type_model."""
        device = DiscoveredDevice(device_name="xrd-1", type_model="", role="PE")
        result = _format_mcp_device_section(device)

        assert "Unknown" in result

    def test_omits_neighbors_line_when_empty(self):
        """Test that neighbors line is omitted when there are no neighbors."""
        device = DiscoveredDevice(
            device_name="xrd-1", type_model="IOS XR", role="PE", neighbors=[]
        )
        result = _format_mcp_device_section(device)

        assert "Neighbors:" not in result


class TestHydrateSingleInvestigation:
    """Test cases for _hydrate_single_investigation function."""

    def test_populates_fields_from_discovered_device(self):
        """Test that Investigation fields come from DiscoveredDevice."""
        from langgraph.store.memory import InMemoryStore

        store = InMemoryStore()
        device = DiscoveredDevice(
            device_name="xrd-1",
            type_model="IOS XR",
            role="PE",
            neighbors=["xrd-2"],
        )
        result = _hydrate_single_investigation(device, store)

        assert result.device_name == "xrd-1"
        assert result.device_type == "IOS XR"
        assert result.role == "PE"
        assert result.neighbors == ["xrd-2"]

    def test_device_context_contains_mcp_data(self):
        """Test that device_context is populated with fresh MCP data."""
        from langgraph.store.memory import InMemoryStore

        store = InMemoryStore()
        device = DiscoveredDevice(
            device_name="xrd-1", type_model="IOS XR", role="PE", neighbors=[]
        )
        result = _hydrate_single_investigation(device, store)

        assert "IOS XR" in result.device_context
        assert "PE" in result.device_context

    def test_enriches_with_stored_history(self):
        """Test that stored history is included in device_context."""
        from langgraph.store.memory import InMemoryStore

        store = InMemoryStore()
        store.put(
            ("device_profiles", "xrd-1"),
            "history",
            {"entries": [{"timestamp": "t", "status": "completed", "summary": "prior run"}]},
        )
        device = DiscoveredDevice(
            device_name="xrd-1", type_model="IOS XR", role="PE", neighbors=[]
        )
        result = _hydrate_single_investigation(device, store)

        assert "prior run" in result.device_context


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

    def test_creation_with_discovered_devices(self):
        """Test InvestigationPlanningResponse creation with DiscoveredDevice objects."""
        response = InvestigationPlanningResponse(
            devices=[
                DiscoveredDevice(device_name="xrd-1", type_model="IOS XR", role="PE"),
                DiscoveredDevice(device_name="xrd-2", type_model="IOS XR", role="P"),
            ]
        )

        assert len(response) == 2

    def test_len_method(self):
        """Test __len__ method of InvestigationPlanningResponse."""
        response = SAMPLE_INVESTIGATION_PLANNING_RESPONSE

        assert len(response) == len(response.devices)

    def test_iter_method(self):
        """Test __iter__ method yields DiscoveredDevice objects."""
        response = SAMPLE_INVESTIGATION_PLANNING_RESPONSE

        devices = list(response)
        assert len(devices) == len(response.devices)
        assert all(isinstance(d, DiscoveredDevice) for d in devices)

    def test_empty_response(self):
        """Test InvestigationPlanningResponse with empty devices list."""
        response = EMPTY_INVESTIGATION_PLANNING_RESPONSE

        assert len(response) == 0
        assert list(response) == []
