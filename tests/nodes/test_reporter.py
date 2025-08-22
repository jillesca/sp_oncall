"""
Unit tests for reporter.py data building functions.

Tests focus on testing data processing logic, not LLM interactions.
Functions that use invoke() or with_structured_output() are excluded.
"""

import pytest
from unittest.mock import Mock, patch
from dataclasses import replace

from src.nodes.reporter import (
    _build_report_context,
    _add_investigation_details,
    _add_session_context,
    _extract_report_content,
    _update_workflow_session,
    _build_learning_insights_context,
    _log_successful_report_generation,
    _build_reset_state_with_report,
)
from src.nodes.markdown_builder import MarkdownBuilder
from schemas.state import GraphState, WorkflowSession, InvestigationStatus
from tests.data.reporter_data import (
    SAMPLE_GRAPH_STATE_FOR_REPORTING,
    EMPTY_GRAPH_STATE_FOR_REPORTING,
    SAMPLE_WORKFLOW_SESSIONS,
    SAMPLE_AI_RESPONSE,
    SAMPLE_AI_RESPONSE_LIST,
    SAMPLE_FINAL_REPORT,
)


class TestBuildReportContext:
    """Test cases for _build_report_context function."""

    def test_build_report_context_structure(self):
        """Test that report context builds proper markdown structure."""
        result = _build_report_context(SAMPLE_GRAPH_STATE_FOR_REPORTING)

        assert isinstance(result, str)
        assert "# Network Investigation Report Context" in result
        assert "## Original User Query" in result
        assert "## Investigation Overview" in result
        assert "## Device Investigation Results" in result
        assert "## Assessment Results" in result
        assert "## Historical Context" in result

    def test_build_report_context_includes_user_query(self):
        """Test that context includes the user query."""
        result = _build_report_context(SAMPLE_GRAPH_STATE_FOR_REPORTING)

        assert SAMPLE_GRAPH_STATE_FOR_REPORTING.user_query in result

    def test_build_report_context_includes_investigation_overview(self):
        """Test that context includes investigation overview statistics."""
        result = _build_report_context(SAMPLE_GRAPH_STATE_FOR_REPORTING)

        assert "Total devices investigated: 2" in result
        assert "Successfully completed: 1" in result
        assert "Success rate:" in result
        assert "Retry attempts:" in result

    def test_build_report_context_with_empty_investigations(self):
        """Test context building with no investigations."""
        result = _build_report_context(EMPTY_GRAPH_STATE_FOR_REPORTING)

        assert "No device investigations found." in result
        assert "Total devices investigated: 0" in result

    def test_build_report_context_includes_assessment(self):
        """Test that context includes assessment information."""
        result = _build_report_context(SAMPLE_GRAPH_STATE_FOR_REPORTING)

        assert "## Assessment Results" in result
        assert "Objective achieved: True" in result
        assert "Investigation completed successfully" in result

    def test_build_report_context_with_no_assessment(self):
        """Test context building when no assessment is available."""
        state_no_assessment = replace(
            SAMPLE_GRAPH_STATE_FOR_REPORTING, assessment=None
        )
        result = _build_report_context(state_no_assessment)

        assert "No assessment results available." in result

    def test_build_report_context_returns_string(self):
        """Test that function returns a non-empty string."""
        result = _build_report_context(SAMPLE_GRAPH_STATE_FOR_REPORTING)

        assert isinstance(result, str)
        assert len(result) > 0


class TestAddInvestigationDetails:
    """Test cases for _add_investigation_details function."""

    def test_add_investigation_details_structure(self):
        """Test that investigation details are added with proper structure."""
        builder = MarkdownBuilder()
        investigation = SAMPLE_GRAPH_STATE_FOR_REPORTING.investigations[0]

        _add_investigation_details(builder, investigation, 1)
        result = builder.build()

        assert "### Investigation 1: xrd-1" in result
        assert "Status:" in result
        assert "Device Profile:" in result
        assert "Role:" in result
        assert "Priority:" in result

    def test_add_investigation_details_includes_status_icons(self):
        """Test that investigation details include status icons."""
        builder = MarkdownBuilder()
        investigation = SAMPLE_GRAPH_STATE_FOR_REPORTING.investigations[
            0
        ]  # Completed

        _add_investigation_details(builder, investigation, 1)
        result = builder.build()

        assert "✅" in result  # Completed status icon

    def test_add_investigation_details_with_failed_investigation(self):
        """Test investigation details for failed investigation."""
        builder = MarkdownBuilder()
        investigation = SAMPLE_GRAPH_STATE_FOR_REPORTING.investigations[
            1
        ]  # Failed

        _add_investigation_details(builder, investigation, 2)
        result = builder.build()

        assert "❌" in result  # Failed status icon
        assert "**Error Details:** Connection timeout" in result

    def test_add_investigation_details_with_report(self):
        """Test investigation details when report is available."""
        builder = MarkdownBuilder()
        investigation = SAMPLE_GRAPH_STATE_FOR_REPORTING.investigations[0]

        _add_investigation_details(builder, investigation, 1)
        result = builder.build()

        assert "**Investigation Report:**" in result
        assert "Device xrd-1 is healthy" in result

    def test_add_investigation_details_with_dependencies(self):
        """Test investigation details when dependencies are present."""
        builder = MarkdownBuilder()
        investigation = replace(
            SAMPLE_GRAPH_STATE_FOR_REPORTING.investigations[0],
            dependencies=["device1", "device2"],
        )

        _add_investigation_details(builder, investigation, 1)
        result = builder.build()

        assert "Dependencies: device1, device2" in result


class TestAddSessionContext:
    """Test cases for _add_session_context function."""

    def test_add_session_context_with_sessions(self):
        """Test adding session context with workflow sessions."""
        builder = MarkdownBuilder()

        _add_session_context(builder, SAMPLE_WORKFLOW_SESSIONS)
        result = builder.build()

        assert "## Historical Context" in result
        assert "Total investigation sessions: 2" in result
        assert "**Recent Sessions (2):**" in result

    def test_add_session_context_with_empty_sessions(self):
        """Test adding session context with no sessions."""
        builder = MarkdownBuilder()

        _add_session_context(builder, [])
        result = builder.build()

        assert "## Historical Context" in result
        assert "**No historical context available.**" in result
        assert "first investigation session" in result

    def test_add_session_context_includes_session_details(self):
        """Test that session context includes session details."""
        builder = MarkdownBuilder()

        _add_session_context(builder, SAMPLE_WORKFLOW_SESSIONS)
        result = builder.build()

        assert "Session session-1:" in result
        assert "Session session-2:" in result
        assert "Report preview:" in result
        assert "Learned patterns:" in result

    def test_add_session_context_limits_recent_sessions(self):
        """Test that session context limits to recent sessions."""
        # Create more than 3 sessions
        many_sessions = SAMPLE_WORKFLOW_SESSIONS + [
            WorkflowSession(
                session_id="session-3",
                previous_report="Report 3",
                learned_patterns="Pattern 3",
                device_relationships="device3 -> device4",
            ),
            WorkflowSession(
                session_id="session-4",
                previous_report="Report 4",
                learned_patterns="Pattern 4",
                device_relationships="device4 -> device5",
            ),
        ]

        builder = MarkdownBuilder()
        _add_session_context(builder, many_sessions)
        result = builder.build()

        # Should show only last 3 sessions
        assert "**Recent Sessions (3):**" in result


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
        del mock_response.content  # Remove content attribute

        result = _extract_report_content(mock_response)

        assert isinstance(result, str)

    def test_extract_report_content_with_non_string_response(self):
        """Test extraction handles non-string response objects."""
        result = _extract_report_content({"key": "value"})

        assert isinstance(result, str)
        assert "key" in result or "value" in result


class TestUpdateWorkflowSession:
    """Test cases for _update_workflow_session function."""

    @patch("src.nodes.reporter.session._generate_learning_insights_with_llm")
    def test_update_workflow_session_creates_new_session(
        self, mock_generate_insights
    ):
        """Test that function creates a new workflow session."""
        from schemas.learning_insights_schema import LearningInsights

        mock_generate_insights.return_value = LearningInsights(
            learned_patterns="Test patterns",
            device_relationships="Test relationships",
        )

        result = _update_workflow_session(
            SAMPLE_GRAPH_STATE_FOR_REPORTING, SAMPLE_FINAL_REPORT
        )

        assert isinstance(result, list)
        assert len(result) == 2  # Original session + new session

        # New session should be last
        new_session = result[-1]
        assert new_session.previous_report == SAMPLE_FINAL_REPORT
        assert new_session.learned_patterns == "Test patterns"
        assert new_session.device_relationships == "Test relationships"

    @patch("src.nodes.reporter.session._generate_learning_insights_with_llm")
    def test_update_workflow_session_with_empty_state(
        self, mock_generate_insights
    ):
        """Test session update with empty state."""
        from schemas.learning_insights_schema import LearningInsights

        mock_generate_insights.return_value = LearningInsights(
            learned_patterns="", device_relationships=""
        )

        result = _update_workflow_session(
            EMPTY_GRAPH_STATE_FOR_REPORTING, SAMPLE_FINAL_REPORT
        )

        assert isinstance(result, list)
        assert len(result) == 1  # Only new session

        new_session = result[0]
        assert new_session.previous_report == SAMPLE_FINAL_REPORT

    @patch("src.nodes.reporter.session._generate_learning_insights_with_llm")
    def test_update_workflow_session_limits_session_count(
        self, mock_generate_insights
    ):
        """Test that session update limits total session count."""
        from schemas.learning_insights_schema import LearningInsights

        mock_generate_insights.return_value = LearningInsights(
            learned_patterns="Test", device_relationships="Test"
        )

        # Create state with many existing sessions
        many_sessions = [
            WorkflowSession(
                session_id=f"session-{i}",
                previous_report=f"Report {i}",
                learned_patterns="Pattern",
                device_relationships="Relationships",
            )
            for i in range(25)  # More than the 20 limit
        ]

        state_with_many_sessions = replace(
            SAMPLE_GRAPH_STATE_FOR_REPORTING, workflow_session=many_sessions
        )

        result = _update_workflow_session(
            state_with_many_sessions, SAMPLE_FINAL_REPORT
        )

        # Should be limited to 20 sessions
        assert len(result) == 20


class TestBuildLearningInsightsContext:
    """Test cases for _build_learning_insights_context function."""

    def test_build_learning_insights_context_structure(self):
        """Test that insights context builds proper structure."""
        result = _build_learning_insights_context(
            SAMPLE_GRAPH_STATE_FOR_REPORTING
        )

        assert isinstance(result, str)
        assert (
            "# Investigation Data for Learning Insights Extraction" in result
        )
        assert "## Original User Query" in result
        assert "## Investigation Results Summary" in result
        assert "## Detailed Investigation Data" in result

    def test_build_learning_insights_context_includes_summary_stats(self):
        """Test that context includes investigation summary statistics."""
        result = _build_learning_insights_context(
            SAMPLE_GRAPH_STATE_FOR_REPORTING
        )

        assert "Total investigations: 2" in result
        assert "Completed investigations: 1" in result

    def test_build_learning_insights_context_includes_investigation_details(
        self,
    ):
        """Test that context includes detailed investigation information."""
        result = _build_learning_insights_context(
            SAMPLE_GRAPH_STATE_FOR_REPORTING
        )

        assert "### Investigation 1: xrd-1" in result
        assert "### Investigation 2: xrd-2" in result
        assert "Status:" in result
        assert "Device Profile:" in result

    def test_build_learning_insights_context_includes_assessment(self):
        """Test that context includes assessment results when available."""
        result = _build_learning_insights_context(
            SAMPLE_GRAPH_STATE_FOR_REPORTING
        )

        assert "## Assessment Results" in result
        assert "Objective Achieved: True" in result

    def test_build_learning_insights_context_truncates_long_reports(self):
        """Test that context truncates very long investigation reports."""
        long_report = "A" * 1000  # Very long report
        investigation_with_long_report = replace(
            SAMPLE_GRAPH_STATE_FOR_REPORTING.investigations[0],
            report=long_report,
        )

        state_with_long_report = replace(
            SAMPLE_GRAPH_STATE_FOR_REPORTING,
            investigations=[investigation_with_long_report],
        )

        result = _build_learning_insights_context(state_with_long_report)

        # Should be truncated with "..."
        assert "..." in result


class TestLogSuccessfulReportGeneration:
    """Test cases for _log_successful_report_generation function."""

    def test_log_successful_report_generation(self, caplog):
        """Test logging of successful report generation."""
        caplog.clear()

        _log_successful_report_generation(SAMPLE_FINAL_REPORT)

        # Function should complete without error
        assert True

    def test_log_successful_report_generation_with_empty_report(self, caplog):
        """Test logging with empty report."""
        caplog.clear()

        _log_successful_report_generation("")

        # Function should complete without error
        assert True


class TestBuildResetStateWithReport:
    """Test cases for _build_reset_state_with_report function."""

    def test_build_reset_state_with_report_creates_fresh_state(self):
        """Test that function creates a fresh GraphState."""
        updated_sessions = SAMPLE_WORKFLOW_SESSIONS

        result = _build_reset_state_with_report(
            SAMPLE_GRAPH_STATE_FOR_REPORTING,
            SAMPLE_FINAL_REPORT,
            updated_sessions,
        )

        assert isinstance(result, GraphState)
        assert result.user_query == SAMPLE_GRAPH_STATE_FOR_REPORTING.user_query
        assert result.final_report == SAMPLE_FINAL_REPORT
        assert result.workflow_session == updated_sessions

    def test_build_reset_state_with_report_resets_other_fields(self):
        """Test that function resets other state fields to defaults."""
        result = _build_reset_state_with_report(
            SAMPLE_GRAPH_STATE_FOR_REPORTING,
            SAMPLE_FINAL_REPORT,
            SAMPLE_WORKFLOW_SESSIONS,
        )

        # These should be reset to defaults
        assert result.investigations == []
        assert result.current_retries == 0
        assert result.assessment is None

    def test_build_reset_state_with_report_preserves_essential_info(self):
        """Test that function preserves essential information."""
        result = _build_reset_state_with_report(
            SAMPLE_GRAPH_STATE_FOR_REPORTING,
            SAMPLE_FINAL_REPORT,
            SAMPLE_WORKFLOW_SESSIONS,
        )

        # These should be preserved
        assert result.user_query == SAMPLE_GRAPH_STATE_FOR_REPORTING.user_query
        assert result.final_report == SAMPLE_FINAL_REPORT
        assert result.workflow_session == SAMPLE_WORKFLOW_SESSIONS
        assert result.max_retries == 3  # Default value

    def test_build_reset_state_with_report_with_empty_inputs(self):
        """Test function with empty inputs."""
        result = _build_reset_state_with_report(
            EMPTY_GRAPH_STATE_FOR_REPORTING, "", []
        )

        assert isinstance(result, GraphState)
        assert result.final_report == ""
        assert result.workflow_session == []
