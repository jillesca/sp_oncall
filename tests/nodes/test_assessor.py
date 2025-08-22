"""
Unit tests for assessor.py helper functions.

Tests focus on testing data processing logic, not LLM interactions.
Functions that use invoke() or with_structured_output() are excluded.
"""

import pytest
from unittest.mock import Mock
from dataclasses import replace

from src.nodes.assessor.core import objective_assessor_node
from src.nodes.assessor.context import (
    build_assessment_context,
    _add_investigation_details as _add_investigation_to_builder,
    _add_execution_results_to_builder,
)
from src.nodes.assessor.assessment import ensure_proper_assessment_format
from src.nodes.assessor.state import (
    apply_assessment_to_workflow,
    _build_successful_assessment_state,
    _build_retry_or_failed_assessment_state,
    _build_retry_state,
    _build_max_retries_reached_state,
    _get_encouraging_retry_guidance,
    handle_assessment_error,
    _build_error_retry_state,
    _build_error_final_state,
)
from src.nodes.markdown_builder import MarkdownBuilder
from schemas.assessment_schema import AssessmentOutput
from tests.data.assessor_data import (
    SAMPLE_GRAPH_STATE_WITH_INVESTIGATIONS,
    SAMPLE_ASSESSMENT_OUTPUT,
    SAMPLE_ASSESSMENT_DICT,
    EMPTY_GRAPH_STATE,
    RETRY_GRAPH_STATE,
)


class TestBuildAssessmentContext:
    """Test cases for _build_assessment_context function."""

    def test_build_assessment_context_structure(self):
        """Test that assessment context builds proper markdown structure."""
        result = build_assessment_context(
            SAMPLE_GRAPH_STATE_WITH_INVESTIGATIONS
        )

        # Check for required sections
        assert "# Network Investigation Assessment Context" in result
        assert "## User Query" in result
        assert "## Device Investigations" in result
        assert "## Historical Context" in result

        # Check user query is included
        assert "how are my routers PE doing?" in result

    def test_build_assessment_context_with_investigations(self):
        """Test context building with investigations."""
        result = build_assessment_context(
            SAMPLE_GRAPH_STATE_WITH_INVESTIGATIONS
        )

        # Check investigations are included
        assert "### Investigation 1: xrd-1" in result
        assert "### Investigation 2: xrd-2" in result
        assert "**Status:**" in result
        assert "**Device Profile:**" in result
        assert "**Role:**" in result

    def test_build_assessment_context_with_empty_investigations(self):
        """Test context building with no investigations."""
        result = build_assessment_context(EMPTY_GRAPH_STATE)

        assert "No device investigations found." in result
        assert "## Device Investigations" in result

    def test_build_assessment_context_with_retry_info(self):
        """Test context building includes retry information when applicable."""
        result = build_assessment_context(RETRY_GRAPH_STATE)

        assert "## Retry Information" in result
        assert "Current attempt: 1 of 3" in result
        assert "Try a different approach" in result

    def test_build_assessment_context_returns_string(self):
        """Test that function returns a string."""
        result = build_assessment_context(
            SAMPLE_GRAPH_STATE_WITH_INVESTIGATIONS
        )

        assert isinstance(result, str)
        assert len(result) > 0


class TestAddInvestigationToBuilder:
    """Test cases for _add_investigation_to_builder function."""

    def test_add_investigation_structure(self):
        """Test that investigation is added with proper structure."""
        builder = MarkdownBuilder()
        investigation = SAMPLE_GRAPH_STATE_WITH_INVESTIGATIONS.investigations[
            0
        ]

        _add_investigation_to_builder(builder, investigation, 1)
        result = builder.build()

        assert "### Investigation 1: xrd-1" in result
        assert "**Status:**" in result
        assert "**Device Profile:**" in result
        assert "**Role:**" in result
        assert "**Objective:**" in result
        assert "**Working Plan Steps:**" in result

    def test_add_investigation_with_execution_results(self):
        """Test adding investigation with execution results."""
        builder = MarkdownBuilder()
        investigation = replace(
            SAMPLE_GRAPH_STATE_WITH_INVESTIGATIONS.investigations[0],
            execution_results=[
                Mock(
                    function="test_function",
                    params={},
                    error=None,
                    result="test_result",
                )
            ],
        )

        _add_investigation_to_builder(builder, investigation, 1)
        result = builder.build()

        assert "**Execution Results:**" in result

    def test_add_investigation_with_error_details(self):
        """Test adding investigation with error details."""
        builder = MarkdownBuilder()
        investigation = replace(
            SAMPLE_GRAPH_STATE_WITH_INVESTIGATIONS.investigations[0],
            error_details="Test error occurred",
        )

        _add_investigation_to_builder(builder, investigation, 1)
        result = builder.build()

        assert "**Error Details:** Test error occurred" in result

    def test_add_investigation_preserves_builder_state(self):
        """Test that function doesn't break existing builder content."""
        builder = MarkdownBuilder()
        builder.add_header("Existing Content")

        investigation = SAMPLE_GRAPH_STATE_WITH_INVESTIGATIONS.investigations[
            0
        ]
        _add_investigation_to_builder(builder, investigation, 1)
        result = builder.build()

        assert "# Existing Content" in result
        assert "### Investigation 1: xrd-1" in result


class TestEnsureProperAssessmentFormat:
    """Test cases for _ensure_proper_assessment_format function."""

    def test_ensure_format_with_assessment_output(self):
        """Test function handles AssessmentOutput objects correctly."""
        result = ensure_proper_assessment_format(SAMPLE_ASSESSMENT_OUTPUT)

        assert isinstance(result, AssessmentOutput)
        assert result.is_objective_achieved == True
        assert (
            result.notes_for_final_report
            == "Assessment completed successfully"
        )

    def test_ensure_format_with_dict_input(self):
        """Test function converts dict to AssessmentOutput."""
        result = ensure_proper_assessment_format(SAMPLE_ASSESSMENT_DICT)

        assert isinstance(result, AssessmentOutput)
        assert result.is_objective_achieved == True
        assert (
            result.notes_for_final_report
            == "Assessment completed successfully"
        )

    def test_ensure_format_with_incomplete_dict(self):
        """Test function handles incomplete dict gracefully."""
        incomplete_dict = {"is_objective_achieved": True}
        result = ensure_proper_assessment_format(incomplete_dict)

        assert isinstance(result, AssessmentOutput)
        assert result.is_objective_achieved == True
        assert "Assessment incomplete" in result.notes_for_final_report

    def test_ensure_format_with_unexpected_type(self):
        """Test function handles unexpected input types."""
        result = ensure_proper_assessment_format("unexpected string")

        assert isinstance(result, AssessmentOutput)
        assert result.is_objective_achieved == False
        assert "unexpected response type" in result.notes_for_final_report

    def test_ensure_format_preserves_existing_values(self):
        """Test function preserves all valid values from input."""
        test_dict = {
            "is_objective_achieved": False,
            "notes_for_final_report": "Custom notes",
            "feedback_for_retry": "Custom feedback",
        }
        result = ensure_proper_assessment_format(test_dict)

        assert result.is_objective_achieved == False
        assert result.notes_for_final_report == "Custom notes"
        assert result.feedback_for_retry == "Custom feedback"


class TestApplyAssessmentToWorkflow:
    """Test cases for _apply_assessment_to_workflow function."""

    def test_apply_successful_assessment(self):
        """Test applying successful assessment to workflow."""
        assessment = replace(
            SAMPLE_ASSESSMENT_OUTPUT, is_objective_achieved=True
        )
        result = apply_assessment_to_workflow(EMPTY_GRAPH_STATE, assessment)

        assert result.assessment == assessment
        assert result.assessment.is_objective_achieved == True

    def test_apply_failed_assessment(self):
        """Test applying failed assessment to workflow."""
        assessment = replace(
            SAMPLE_ASSESSMENT_OUTPUT, is_objective_achieved=False
        )
        result = apply_assessment_to_workflow(EMPTY_GRAPH_STATE, assessment)

        # The function may modify the assessment (e.g., add retry feedback)
        assert result.assessment.is_objective_achieved == False
        assert result.current_retries == 1  # Should increment retries

    def test_apply_assessment_preserves_state(self):
        """Test that applying assessment preserves other state fields."""
        assessment = SAMPLE_ASSESSMENT_OUTPUT
        result = apply_assessment_to_workflow(
            SAMPLE_GRAPH_STATE_WITH_INVESTIGATIONS, assessment
        )

        assert (
            result.user_query
            == SAMPLE_GRAPH_STATE_WITH_INVESTIGATIONS.user_query
        )
        assert len(result.investigations) == len(
            SAMPLE_GRAPH_STATE_WITH_INVESTIGATIONS.investigations
        )
        assert (
            result.max_retries
            == SAMPLE_GRAPH_STATE_WITH_INVESTIGATIONS.max_retries
        )


class TestBuildAssessmentStates:
    """Test cases for state building functions."""

    def test_build_successful_assessment_state(self):
        """Test building successful assessment state."""
        assessment = replace(
            SAMPLE_ASSESSMENT_OUTPUT, is_objective_achieved=True
        )
        result = _build_successful_assessment_state(
            EMPTY_GRAPH_STATE, assessment
        )

        assert result.assessment == assessment
        assert result.assessment.is_objective_achieved == True

    def test_build_retry_state(self):
        """Test building retry state."""
        assessment = replace(
            SAMPLE_ASSESSMENT_OUTPUT,
            is_objective_achieved=False,
            feedback_for_retry="Try again",
        )
        result = _build_retry_state(EMPTY_GRAPH_STATE, assessment)

        assert result.current_retries == 1
        assert result.assessment.feedback_for_retry == "Try again"

    def test_build_retry_state_increments_retries(self):
        """Test that retry state increments retry counter."""
        state_with_retries = replace(EMPTY_GRAPH_STATE, current_retries=1)
        assessment = replace(
            SAMPLE_ASSESSMENT_OUTPUT, is_objective_achieved=False
        )
        result = _build_retry_state(state_with_retries, assessment)

        assert result.current_retries == 2

    def test_build_max_retries_reached_state(self):
        """Test building state when max retries reached."""
        state_at_max = replace(
            EMPTY_GRAPH_STATE, current_retries=3, max_retries=3
        )
        assessment = replace(
            SAMPLE_ASSESSMENT_OUTPUT, is_objective_achieved=False
        )
        result = _build_max_retries_reached_state(state_at_max, assessment)

        assert (
            result.assessment.is_objective_achieved == True
        )  # Forced completion
        assert "not achieved after" in result.assessment.notes_for_final_report

    def test_get_encouraging_retry_guidance(self):
        """Test encouraging retry guidance generation."""
        guidance = _get_encouraging_retry_guidance()

        assert isinstance(guidance, str)
        assert len(guidance) > 0
        assert "different approach" in guidance.lower()


class TestErrorHandling:
    """Test cases for error handling functions."""

    def test_handle_assessment_error_with_retries_available(self):
        """Test error handling when retries are available."""
        error = ValueError("Test error")
        result = handle_assessment_error(EMPTY_GRAPH_STATE, error)

        assert result.current_retries == 1
        assert result.assessment.is_objective_achieved == False
        assert "Test error" in result.assessment.notes_for_final_report

    def test_handle_assessment_error_at_max_retries(self):
        """Test error handling when at max retries."""
        error = ValueError("Test error")
        state_at_max = replace(
            EMPTY_GRAPH_STATE, current_retries=3, max_retries=3
        )
        result = handle_assessment_error(state_at_max, error)

        assert (
            result.assessment.is_objective_achieved == True
        )  # Forced completion
        assert "Test error" in result.assessment.notes_for_final_report

    def test_build_error_retry_state(self):
        """Test building error retry state."""
        error = RuntimeError("Runtime error occurred")
        result = _build_error_retry_state(EMPTY_GRAPH_STATE, error)

        assert result.current_retries == 1
        assert result.assessment.is_objective_achieved == False
        assert (
            "Runtime error occurred"
            in result.assessment.notes_for_final_report
        )

    def test_build_error_final_state(self):
        """Test building error final state."""
        error = RuntimeError("Final error")
        result = _build_error_final_state(EMPTY_GRAPH_STATE, error)

        assert (
            result.assessment.is_objective_achieved == True
        )  # Forced completion
        assert "Final error" in result.assessment.notes_for_final_report


class TestMarkdownBuilderHelpers:
    """Test cases for markdown builder helper functions."""

    def test_add_execution_results_to_builder_with_results(self):
        """Test adding execution results to builder."""
        builder = MarkdownBuilder()
        mock_results = [
            Mock(
                function="test_func",
                params={"param": "value"},
                error=None,
                result="success",
            ),
            Mock(
                function="test_func2",
                params={},
                error="test error",
                result=None,
            ),
        ]

        _add_execution_results_to_builder(builder, mock_results)
        result = builder.build()

        assert "**Execution Results:**" in result
        assert "2 tool calls executed" in result
        assert "**Tool Call 1:** test_func" in result
        assert "**Tool Call 2:** test_func2" in result

    def test_add_execution_results_to_builder_empty(self):
        """Test adding execution results with empty list."""
        builder = MarkdownBuilder()

        _add_execution_results_to_builder(builder, [])
        result = builder.build()

        assert (
            "**Execution Results:** No execution results available" in result
        )
