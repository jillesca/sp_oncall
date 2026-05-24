"""
Unit tests for src/util/validation.py.

Tests focus on the validation gate logic, validators, and helper functions.
LLM interactions are mocked.
"""

from dataclasses import dataclass
from typing import List
from unittest.mock import Mock, call

import pytest

from src.util.validation import (
    _build_retry_prompt,
    _get_field,
    _run_validators,
    validate_investigation_planning,
    validate_planning_response,
    validate_structured_output,
)


# ---------------------------------------------------------------------------
# Minimal schemas for testing without importing real node schemas
# ---------------------------------------------------------------------------


@dataclass
class _DevicePlan:
    device_name: str = ""
    objective: str = ""
    working_plan_steps: str = ""


@dataclass
class _DiscoveredDevice:
    device_name: str = ""
    type_model: str = ""
    role: str = ""


@dataclass
class _InvestigationResponse:
    devices: List = None

    def __post_init__(self):
        if self.devices is None:
            self.devices = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_model(return_values):
    """Return a mock model whose structured_output.invoke returns values in sequence."""
    mock_structured = Mock()
    mock_structured.invoke.side_effect = return_values
    mock_model = Mock()
    mock_model.with_structured_output.return_value = mock_structured
    return mock_model, mock_structured


def _no_violations(result):
    return []


def _always_violates(result):
    return ["always fails"]


# ---------------------------------------------------------------------------
# validate_structured_output
# ---------------------------------------------------------------------------


class TestValidateStructuredOutput:
    """Tests for validate_structured_output."""

    def test_returns_result_and_empty_violations_when_valid(self):
        """Valid result on first attempt returns (result, [])."""
        valid_result = _DevicePlan("xrd-1", "check health", "step 1")
        model, structured = _make_model([valid_result])

        result, violations = validate_structured_output(
            raw_text="some text",
            schema=_DevicePlan,
            model=model,
            validators=[_no_violations],
        )

        assert result is valid_result
        assert violations == []
        assert structured.invoke.call_count == 1

    def test_retries_on_violations_and_succeeds(self):
        """When first attempt has violations and retry succeeds, returns valid result."""
        invalid_result = _DevicePlan("", "")
        valid_result = _DevicePlan("xrd-1", "check", "steps")
        model, structured = _make_model([invalid_result, valid_result])

        def validator(result):
            name = result.device_name if hasattr(result, "device_name") else result.get("device_name", "")
            if not name:
                return ["device_name is empty"]
            return []

        result, violations = validate_structured_output(
            raw_text="original",
            schema=_DevicePlan,
            model=model,
            validators=[validator],
            max_attempts=2,
        )

        assert result is valid_result
        assert violations == []
        assert structured.invoke.call_count == 2

    def test_returns_best_effort_after_exhausting_attempts(self):
        """When all attempts fail validation, returns last result with violations."""
        bad_result = _DevicePlan("", "")
        model, structured = _make_model([bad_result, bad_result, bad_result])

        result, violations = validate_structured_output(
            raw_text="text",
            schema=_DevicePlan,
            model=model,
            validators=[_always_violates],
            max_attempts=2,
        )

        assert result is bad_result
        assert violations == ["always fails"]
        assert structured.invoke.call_count == 3

    def test_never_raises_on_exception(self):
        """Exceptions during parsing are caught; returns (None, []) after all attempts."""
        model, structured = _make_model(
            [RuntimeError("parse error"), RuntimeError("parse error")]
        )

        result, violations = validate_structured_output(
            raw_text="text",
            schema=_DevicePlan,
            model=model,
            validators=[_no_violations],
            max_attempts=1,
        )

        assert result is None
        assert violations == []

    def test_retries_on_exception_then_succeeds(self):
        """An exception on first attempt allows retry; succeeds on second."""
        valid_result = _DevicePlan("xrd-1", "check", "steps")
        model, structured = _make_model([RuntimeError("transient"), valid_result])

        result, violations = validate_structured_output(
            raw_text="text",
            schema=_DevicePlan,
            model=model,
            validators=[_no_violations],
            max_attempts=1,
        )

        assert result is valid_result
        assert violations == []
        assert structured.invoke.call_count == 2

    def test_retry_prompt_is_used_on_second_attempt(self):
        """The second attempt receives a retry prompt, not the original text."""
        invalid_result = _DevicePlan("")
        valid_result = _DevicePlan("xrd-1", "check", "steps")
        model, structured = _make_model([invalid_result, valid_result])

        validate_structured_output(
            raw_text="original input",
            schema=_DevicePlan,
            model=model,
            validators=[_always_violates],
            max_attempts=1,
        )

        second_call_input = structured.invoke.call_args_list[1]
        second_input_text = second_call_input[1]["input"]
        assert "original input" in second_input_text
        assert "always fails" in second_input_text

    def test_max_attempts_zero_means_one_attempt_total(self):
        """max_attempts=0 means only the initial attempt — no retries."""
        bad_result = _DevicePlan("")
        model, structured = _make_model([bad_result])

        result, violations = validate_structured_output(
            raw_text="text",
            schema=_DevicePlan,
            model=model,
            validators=[_always_violates],
            max_attempts=0,
        )

        assert structured.invoke.call_count == 1
        assert violations == ["always fails"]


# ---------------------------------------------------------------------------
# validate_planning_response
# ---------------------------------------------------------------------------


class TestValidatePlanningResponse:
    """Tests for validate_planning_response validator (single DevicePlan)."""

    def test_valid_device_plan_returns_no_violations(self):
        """A well-formed DevicePlan produces no violations."""
        result = _DevicePlan("xrd-1", "Check health", "Step 1: check system")
        assert validate_planning_response(result) == []

    def test_empty_device_name_returns_violation(self):
        """A DevicePlan with empty device_name triggers a violation."""
        result = _DevicePlan("", "objective", "steps")
        violations = validate_planning_response(result)
        assert any("device_name" in v for v in violations)

    def test_empty_working_plan_steps_returns_violation(self):
        """A DevicePlan with empty working_plan_steps triggers a violation."""
        result = _DevicePlan("xrd-1", "objective", "")
        violations = validate_planning_response(result)
        assert any("working_plan_steps" in v for v in violations)

    def test_both_empty_returns_two_violations(self):
        """Both device_name and working_plan_steps empty yields two violations."""
        result = _DevicePlan("", "", "")
        violations = validate_planning_response(result)
        assert len(violations) == 2

    def test_works_with_dict_input(self):
        """Validator handles dict representation as returned by some LLM providers."""
        result = {"device_name": "", "working_plan_steps": "steps"}
        violations = validate_planning_response(result)
        assert any("device_name" in v for v in violations)

    def test_dict_input_valid_returns_no_violations(self):
        """Dict input with all fields populated returns no violations."""
        result = {"device_name": "xrd-1", "working_plan_steps": "Step 1"}
        assert validate_planning_response(result) == []


# ---------------------------------------------------------------------------
# validate_investigation_planning
# ---------------------------------------------------------------------------


class TestValidateInvestigationPlanning:
    """Tests for validate_investigation_planning validator."""

    def test_valid_response_returns_no_violations(self):
        """A well-formed response with discovered devices produces no violations."""
        result = _InvestigationResponse(
            devices=[
                _DiscoveredDevice(device_name="xrd-1"),
                _DiscoveredDevice(device_name="xrd-2"),
            ]
        )
        assert validate_investigation_planning(result) == []

    def test_empty_devices_returns_violation(self):
        """An empty devices list triggers a violation."""
        result = _InvestigationResponse(devices=[])
        violations = validate_investigation_planning(result)
        assert any("empty" in v for v in violations)

    def test_empty_name_in_list_returns_violation(self):
        """A device entry with empty device_name triggers a violation."""
        result = _InvestigationResponse(devices=[_DiscoveredDevice(device_name="")])
        violations = validate_investigation_planning(result)
        assert any("device_name" in v for v in violations)

    def test_works_with_dict_input(self):
        """Validator handles dict representation as returned by some LLM providers."""
        result = {"devices": [{"device_name": ""}]}
        violations = validate_investigation_planning(result)
        assert any("device_name" in v for v in violations)

    def test_dict_empty_devices_returns_violation(self):
        """Dict with empty devices list triggers violation."""
        violations = validate_investigation_planning({"devices": []})
        assert any("empty" in v for v in violations)

    def test_dict_valid_devices_returns_no_violations(self):
        """Dict with named devices returns no violations."""
        result = {"devices": [{"device_name": "xrd-1"}, {"device_name": "xrd-2"}]}
        assert validate_investigation_planning(result) == []


# ---------------------------------------------------------------------------
# _get_field
# ---------------------------------------------------------------------------


class TestGetField:
    """Tests for _get_field helper."""

    def test_gets_attribute_from_object(self):
        obj = _DevicePlan(device_name="xrd-1", working_plan_steps="steps")
        assert _get_field(obj, "device_name", "") == "xrd-1"

    def test_gets_key_from_dict(self):
        assert _get_field({"key": "value"}, "key", "") == "value"

    def test_returns_default_for_missing_attribute(self):
        assert _get_field(_DevicePlan(), "nonexistent", "default") == "default"

    def test_returns_default_for_missing_key(self):
        assert _get_field({}, "missing", 42) == 42


# ---------------------------------------------------------------------------
# _build_retry_prompt
# ---------------------------------------------------------------------------


class TestBuildRetryPrompt:
    """Tests for _build_retry_prompt helper."""

    def test_contains_original_text(self):
        prompt = _build_retry_prompt("original text", ["issue 1"])
        assert "original text" in prompt

    def test_contains_violations(self):
        prompt = _build_retry_prompt("text", ["device_name is empty", "steps empty"])
        assert "device_name is empty" in prompt
        assert "steps empty" in prompt

    def test_formats_violations_as_list(self):
        prompt = _build_retry_prompt("text", ["issue A", "issue B"])
        assert "- issue A" in prompt
        assert "- issue B" in prompt

    def test_handles_non_string_original_input(self):
        prompt = _build_retry_prompt(["list", "content"], ["violation"])
        assert isinstance(prompt, str)
        assert "violation" in prompt


# ---------------------------------------------------------------------------
# _run_validators
# ---------------------------------------------------------------------------


class TestRunValidators:
    """Tests for _run_validators helper."""

    def test_collects_violations_from_all_validators(self):
        def v1(r):
            return ["v1 violation"]

        def v2(r):
            return ["v2 violation"]

        violations = _run_validators("result", [v1, v2])
        assert violations == ["v1 violation", "v2 violation"]

    def test_returns_empty_when_all_valid(self):
        assert _run_validators("result", [_no_violations]) == []

    def test_returns_empty_with_no_validators(self):
        assert _run_validators("result", []) == []
