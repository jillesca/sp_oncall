"""
Unit tests for the planner node.

Tests focus on data processing logic, not LLM interactions.
Functions that use invoke() or with_structured_output() are excluded.
"""

import pytest
from unittest.mock import Mock, patch

from src.nodes.planner.planning import (
    DevicePlan,
    load_available_skills,
    execute_plan_selection,
    process_device_plan_response,
)
from src.nodes.planner.context import build_planning_context
from schemas.state import GraphState, Investigation
from tests.data.planner_data import (
    SAMPLE_INVESTIGATION_FOR_PLANNING,
    SAMPLE_DEVICE_PLAN,
    SAMPLE_PLANNING_ERROR,
)


class TestLoadAvailableSkills:
    """Test cases for load_available_skills function."""

    @patch("src.nodes.planner.planning.load_skills")
    def test_load_all_skills_for_manual_query(self, mock_load_skills):
        """When event_type is None, all skills are loaded without filtering."""
        mock_load_skills.return_value = "# Skill 1\n\n---\n\n# Skill 2"

        result = load_available_skills(event_type=None)

        assert isinstance(result, str)
        assert len(result) > 0
        mock_load_skills.assert_called_once_with()

    @patch("src.nodes.planner.planning.get_skills_for_alert")
    @patch("src.nodes.planner.planning.load_skills")
    def test_load_filtered_skills_for_alert(
        self, mock_load_skills, mock_get_skills
    ):
        """When event_type is present, skills are filtered via the routing table."""
        mock_get_skills.return_value = [
            "check_interface_status",
            "general_device_health_check",
        ]
        mock_load_skills.return_value = "# Check Interface Status\n..."

        result = load_available_skills(event_type="interface_state")

        assert isinstance(result, str)
        mock_get_skills.assert_called_once_with("interface_state")
        mock_load_skills.assert_called_once_with(
            ["check_interface_status", "general_device_health_check"]
        )

    @patch("src.nodes.planner.planning.load_skills")
    def test_load_available_skills_returns_string(self, mock_load_skills):
        """Return value is always a string even when no skills are found."""
        mock_load_skills.return_value = "No skills available."

        result = load_available_skills()

        assert isinstance(result, str)


class TestBuildPlanningContext:
    """Test cases for build_planning_context function."""

    def test_build_planning_context_includes_device_name(self):
        """Context includes the target device name."""
        result = build_planning_context(SAMPLE_INVESTIGATION_FOR_PLANNING)

        assert isinstance(result, str)
        assert "xrd-1" in result

    def test_build_planning_context_includes_role(self):
        """Context includes the device role when set."""
        result = build_planning_context(SAMPLE_INVESTIGATION_FOR_PLANNING)

        assert "PE" in result

    def test_build_planning_context_with_empty_profile(self):
        """Context handles empty device profile gracefully."""
        investigation = Investigation(device_name="xrd-3")

        result = build_planning_context(investigation)

        assert isinstance(result, str)
        assert "xrd-3" in result
        assert "No context available" in result

    def test_build_planning_context_with_empty_role(self):
        """Context shows 'Unknown' when role is empty."""
        investigation = Investigation(device_name="xrd-3")

        result = build_planning_context(investigation)

        assert "Unknown" in result

    def test_build_planning_context_structure(self):
        """Context has proper markdown structure."""
        result = build_planning_context(SAMPLE_INVESTIGATION_FOR_PLANNING)

        lines = result.split("\n")
        assert any(line.startswith("#") for line in lines)


class TestDevicePlanDataClass:
    """Test cases for DevicePlan data class."""

    def test_device_plan_creation(self):
        """Test DevicePlan creation with required fields."""
        plan = DevicePlan(
            device_name="test-device",
            objective="Test objective",
            working_plan_steps="Step 1: Test step",
        )

        assert plan.device_name == "test-device"
        assert plan.objective == "Test objective"
        assert plan.working_plan_steps == "Step 1: Test step"

    def test_device_plan_default_values(self):
        """Test DevicePlan has sensible defaults."""
        plan = DevicePlan(device_name="test-device")

        assert plan.device_name == "test-device"
        assert plan.objective == ""
        assert plan.working_plan_steps == ""

    def test_device_plan_sample_data(self):
        """Sample data matches expected shape."""
        assert SAMPLE_DEVICE_PLAN.device_name == "xrd-1"
        assert "PE router" in SAMPLE_DEVICE_PLAN.objective
        assert "Step 1" in SAMPLE_DEVICE_PLAN.working_plan_steps
