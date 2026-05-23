"""
Unit tests for reporter node data building functions.

Tests focus on testing data processing logic, not LLM interactions.
Functions that use invoke() or with_structured_output() are excluded.
"""

import pytest
from unittest.mock import Mock, patch
from dataclasses import replace

from src.nodes.reporter.core import (
    investigation_report_node,
    _log_successful_report_generation,
)
from src.nodes.reporter.context import (
    build_report_context,
    _add_single_investigation_details,
)
from src.nodes.reporter.generation import _extract_report_content
from src.nodes.markdown_builder import MarkdownBuilder
from schemas.state import GraphState, InvestigationStatus
from tests.data.reporter_data import (
    SAMPLE_GRAPH_STATE_FOR_REPORTING,
    EMPTY_GRAPH_STATE_FOR_REPORTING,
    SAMPLE_AI_RESPONSE,
    SAMPLE_AI_RESPONSE_LIST,
    SAMPLE_FINAL_REPORT,
)


class TestBuildReportContext:
    """Test cases for build_report_context function."""

    def test_build_report_context_structure(self):
        """Test that report context builds proper markdown structure."""
        result = build_report_context(SAMPLE_GRAPH_STATE_FOR_REPORTING)

        assert isinstance(result, str)
        assert "# Network Investigation Report Context" in result
        assert "## Trigger Context" in result
        assert "## Investigation Overview" in result
        assert "## Device Investigation Results" in result

    def test_build_report_context_includes_user_query(self):
        """Test that context includes the user query."""
        result = build_report_context(SAMPLE_GRAPH_STATE_FOR_REPORTING)

        assert SAMPLE_GRAPH_STATE_FOR_REPORTING.trigger_context in result

    def test_build_report_context_includes_investigation_overview(self):
        """Test that context includes investigation overview statistics."""
        result = build_report_context(SAMPLE_GRAPH_STATE_FOR_REPORTING)

        assert "Total devices investigated: 2" in result
        assert "Successfully completed: 1" in result
        assert "Success rate:" in result

    def test_build_report_context_with_empty_investigations(self):
        """Test context building with no investigations."""
        result = build_report_context(EMPTY_GRAPH_STATE_FOR_REPORTING)

        assert "No device investigations found." in result
        assert "Total devices investigated: 0" in result

    def test_build_report_context_returns_string(self):
        """Test that function returns a non-empty string."""
        result = build_report_context(SAMPLE_GRAPH_STATE_FOR_REPORTING)

        assert isinstance(result, str)
        assert len(result) > 0


class TestAddInvestigationDetails:
    """Test cases for _add_single_investigation_details function."""

    def test_add_investigation_details_structure(self):
        """Test that investigation details are added with proper structure."""
        builder = MarkdownBuilder()
        investigation = SAMPLE_GRAPH_STATE_FOR_REPORTING.investigations[0]

        _add_single_investigation_details(builder, investigation, 1)
        result = builder.build()

        assert "### Investigation 1: xrd-1" in result
        assert "Status:" in result
        assert "Device Profile:" in result
        assert "Role:" in result

    def test_add_investigation_details_includes_status_icons(self):
        """Test that investigation details include status icons."""
        builder = MarkdownBuilder()
        investigation = SAMPLE_GRAPH_STATE_FOR_REPORTING.investigations[0]  # Completed

        _add_single_investigation_details(builder, investigation, 1)
        result = builder.build()

        assert "✅" in result

    def test_add_investigation_details_with_failed_investigation(self):
        """Test investigation details for failed investigation."""
        builder = MarkdownBuilder()
        investigation = SAMPLE_GRAPH_STATE_FOR_REPORTING.investigations[1]  # Failed

        _add_single_investigation_details(builder, investigation, 2)
        result = builder.build()

        assert "❌" in result
        assert "**Error Details:** Connection timeout" in result

    def test_add_investigation_details_with_report(self):
        """Test investigation details when report is available."""
        builder = MarkdownBuilder()
        investigation = SAMPLE_GRAPH_STATE_FOR_REPORTING.investigations[0]

        _add_single_investigation_details(builder, investigation, 1)
        result = builder.build()

        assert "**Investigation Report:**" in result
        assert "Device xrd-1 is healthy" in result


class TestExtractReportContent:
    """Test cases for _extract_report_content function."""

    def test_extract_report_content_with_string_content(self):
        """Test extraction from response with string content."""
        result = _extract_report_content(SAMPLE_AI_RESPONSE)

        assert isinstance(result, str)
        assert result == "Generated report content"

    def test_extract_report_content_with_list_content(self):
        """Test extraction from response with list content."""
        result = _extract_report_content(SAMPLE_AI_RESPONSE_LIST)

        assert isinstance(result, str)
        assert "Part 1 of report" in result
        assert "Part 2 of report" in result

    def test_extract_report_content_with_no_content_attribute(self):
        """Test extraction from response without content attribute."""
        mock_response = Mock()
        mock_response.content = None
        del mock_response.content

        result = _extract_report_content(mock_response)

        assert isinstance(result, str)

    def test_extract_report_content_with_non_string_response(self):
        """Test extraction handles non-string response objects."""
        result = _extract_report_content({"key": "value"})

        assert isinstance(result, str)
        assert "key" in result or "value" in result


class TestLogSuccessfulReportGeneration:
    """Test cases for _log_successful_report_generation function."""

    def test_log_successful_report_generation(self, caplog):
        """Test logging of successful report generation."""
        caplog.clear()

        _log_successful_report_generation(SAMPLE_FINAL_REPORT)

        assert True  # Function should complete without error

    def test_log_successful_report_generation_with_empty_report(self, caplog):
        """Test logging with empty report."""
        caplog.clear()

        _log_successful_report_generation("")

        assert True  # Function should complete without error
