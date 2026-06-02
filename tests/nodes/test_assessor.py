"""
Unit tests for assessor node helper functions.

Tests focus on data processing logic, not LLM interactions.
Functions that use invoke() or with_structured_output() are excluded.
"""

import pytest
from dataclasses import replace

from src.nodes.assessor.context import build_phase_assessment_context
from src.nodes.assessor.assessment import ensure_proper_assessment_format
from schemas.assessment_schema import AssessmentOutput
from tests.data.assessor_data import (
    SAMPLE_TRIGGER_CONTEXT,
    SAMPLE_INVESTIGATION_XRD1,
    SAMPLE_INVESTIGATION_XRD2,
    SAMPLE_ASSESSMENT_OUTPUT,
    SAMPLE_ASSESSMENT_DICT,
)


class TestBuildPhaseAssessmentContext:
    """Tests for build_phase_assessment_context — the minimal assessor context."""

    def test_returns_non_empty_string(self):
        result = build_phase_assessment_context(
            [SAMPLE_INVESTIGATION_XRD1], SAMPLE_TRIGGER_CONTEXT
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_includes_trigger_context(self):
        result = build_phase_assessment_context(
            [SAMPLE_INVESTIGATION_XRD1], SAMPLE_TRIGGER_CONTEXT
        )
        assert SAMPLE_TRIGGER_CONTEXT in result
        assert "<TRIGGER_CONTEXT>" in result

    def test_includes_device_name_and_role(self):
        result = build_phase_assessment_context(
            [SAMPLE_INVESTIGATION_XRD1], SAMPLE_TRIGGER_CONTEXT
        )
        assert "xrd-1" in result
        assert "PE" in result

    def test_includes_objective(self):
        result = build_phase_assessment_context(
            [SAMPLE_INVESTIGATION_XRD1], SAMPLE_TRIGGER_CONTEXT
        )
        assert SAMPLE_INVESTIGATION_XRD1.objective in result

    def test_includes_report(self):
        result = build_phase_assessment_context(
            [SAMPLE_INVESTIGATION_XRD1], SAMPLE_TRIGGER_CONTEXT
        )
        assert SAMPLE_INVESTIGATION_XRD1.report in result

    def test_no_raw_tool_json_in_output(self):
        """Tool call JSON should never appear in the assessor context."""
        result = build_phase_assessment_context(
            [SAMPLE_INVESTIGATION_XRD1], SAMPLE_TRIGGER_CONTEXT
        )
        assert "tool_call_id" not in result
        assert "raw_content" not in result

    def test_multiple_investigations_included(self):
        result = build_phase_assessment_context(
            [SAMPLE_INVESTIGATION_XRD1, SAMPLE_INVESTIGATION_XRD2],
            SAMPLE_TRIGGER_CONTEXT,
        )
        assert "xrd-1" in result
        assert "xrd-2" in result

    def test_missing_report_shows_placeholder(self):
        no_report = replace(SAMPLE_INVESTIGATION_XRD1, report=None)
        result = build_phase_assessment_context([no_report], SAMPLE_TRIGGER_CONTEXT)
        assert "No report available" in result

    def test_error_details_shown_when_no_report(self):
        with_error = replace(
            SAMPLE_INVESTIGATION_XRD1,
            report=None,
            error_details="Connection timeout",
        )
        result = build_phase_assessment_context([with_error], SAMPLE_TRIGGER_CONTEXT)
        assert "Connection timeout" in result


class TestEnsureProperAssessmentFormat:
    """Tests for ensure_proper_assessment_format."""

    def test_passes_through_assessment_output(self):
        result = ensure_proper_assessment_format(SAMPLE_ASSESSMENT_OUTPUT)
        assert isinstance(result, AssessmentOutput)
        assert result.is_objective_achieved is True
        assert result.notes_for_final_report == "Assessment completed successfully"

    def test_converts_dict_to_assessment_output(self):
        result = ensure_proper_assessment_format(SAMPLE_ASSESSMENT_DICT)
        assert isinstance(result, AssessmentOutput)
        assert result.is_objective_achieved is True
        assert result.notes_for_final_report == "Assessment completed successfully"

    def test_incomplete_dict_gets_default_notes(self):
        result = ensure_proper_assessment_format({"is_objective_achieved": True})
        assert isinstance(result, AssessmentOutput)
        assert result.is_objective_achieved is True
        assert "Assessment incomplete" in result.notes_for_final_report

    def test_unexpected_type_returns_failed_assessment(self):
        result = ensure_proper_assessment_format("unexpected string")
        assert isinstance(result, AssessmentOutput)
        assert result.is_objective_achieved is False
        assert "unexpected response type" in result.notes_for_final_report

    def test_preserves_all_fields_from_dict(self):
        input_dict = {
            "is_objective_achieved": False,
            "notes_for_final_report": "Custom notes",
            "feedback_for_retry": "Retry step 2",
        }
        result = ensure_proper_assessment_format(input_dict)
        assert result.is_objective_achieved is False
        assert result.notes_for_final_report == "Custom notes"
        assert result.feedback_for_retry == "Retry step 2"
