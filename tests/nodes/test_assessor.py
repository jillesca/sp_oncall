"""
Unit tests for assessor node helper functions.

Tests focus on testing data processing logic, not LLM interactions.
Functions that use invoke() or with_structured_output() are excluded.
"""

import pytest
from unittest.mock import Mock
from dataclasses import replace

from src.nodes.assessor.context import (
    build_assessment_context,
    _add_investigation_details as _add_investigation_to_builder,
    _add_execution_results_to_builder,
)
from src.nodes.assessor.assessment import ensure_proper_assessment_format
from src.nodes.markdown_builder import MarkdownBuilder
from schemas.assessment_schema import AssessmentOutput
from tests.data.assessor_data import (
    SAMPLE_TRIGGER_CONTEXT,
    SAMPLE_INVESTIGATION_XRD1,
    SAMPLE_INVESTIGATION_XRD2,
    SAMPLE_ASSESSMENT_OUTPUT,
    SAMPLE_ASSESSMENT_DICT,
)


class TestBuildAssessmentContext:
    """Test cases for build_assessment_context function."""

    def test_build_assessment_context_structure(self):
        """Test that assessment context builds proper markdown structure."""
        result = build_assessment_context(
            SAMPLE_INVESTIGATION_XRD1, SAMPLE_TRIGGER_CONTEXT
        )

        assert "# Device Investigation Assessment Context" in result
        assert "## Trigger Context" in result
        assert SAMPLE_TRIGGER_CONTEXT in result

    def test_build_assessment_context_with_investigation(self):
        """Test context building includes investigation details."""
        result = build_assessment_context(
            SAMPLE_INVESTIGATION_XRD1, SAMPLE_TRIGGER_CONTEXT
        )

        assert "xrd-1" in result
        assert "**Status:**" in result
        assert "**Device Context:**" in result
        assert "**Role:**" in result

    def test_build_assessment_context_returns_string(self):
        """Test that function returns a non-empty string."""
        result = build_assessment_context(
            SAMPLE_INVESTIGATION_XRD1, SAMPLE_TRIGGER_CONTEXT
        )

        assert isinstance(result, str)
        assert len(result) > 0


class TestAddInvestigationToBuilder:
    """Test cases for _add_investigation_to_builder function."""

    def test_add_investigation_structure(self):
        """Test that investigation is added with proper structure."""
        builder = MarkdownBuilder()

        _add_investigation_to_builder(builder, SAMPLE_INVESTIGATION_XRD1)
        result = builder.build()

        assert "xrd-1" in result
        assert "**Status:**" in result
        assert "**Device Context:**" in result
        assert "**Role:**" in result
        assert "**Objective:**" in result
        assert "**Working Plan Steps:**" in result

    def test_add_investigation_with_execution_results(self):
        """Test adding investigation with execution results."""
        builder = MarkdownBuilder()
        investigation = replace(
            SAMPLE_INVESTIGATION_XRD1,
            execution_results=[
                Mock(
                    function="test_function",
                    params={},
                    error=None,
                    result="test_result",
                )
            ],
        )

        _add_investigation_to_builder(builder, investigation)
        result = builder.build()

        assert "**Execution Results:**" in result

    def test_add_investigation_with_error_details(self):
        """Test adding investigation with error details."""
        builder = MarkdownBuilder()
        investigation = replace(
            SAMPLE_INVESTIGATION_XRD1,
            error_details="Test error occurred",
        )

        _add_investigation_to_builder(builder, investigation)
        result = builder.build()

        assert "**Error Details:** Test error occurred" in result

    def test_add_investigation_preserves_builder_state(self):
        """Test that function doesn't break existing builder content."""
        builder = MarkdownBuilder()
        builder.add_header("Existing Content")

        _add_investigation_to_builder(builder, SAMPLE_INVESTIGATION_XRD1)
        result = builder.build()

        assert "# Existing Content" in result
        assert "xrd-1" in result


class TestEnsureProperAssessmentFormat:
    """Test cases for ensure_proper_assessment_format function."""

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
