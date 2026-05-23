"""
Unit tests for planner.py data processing functions.

Tests focus on testing data processing logic, not LLM interactions.
Functions that use invoke() or with_structured_output() are excluded.
"""

import pytest
from unittest.mock import Mock, patch
from dataclasses import replace

from src.nodes.planner.core import planner_node
from src.nodes.planner.planning import (
    load_available_skills,
    execute_plan_selection,
    process_planning_response,
    DevicePlan,
    PlanningResponse,
)
from src.nodes.planner.context import (
    extract_investigations_summary,
    build_planning_context,
)
from src.nodes.planner.state import (
    build_successful_planning_state,
    build_failed_planning_state,
)
from schemas.state import GraphState, Investigation
from tests.data.planner_data import (
    SAMPLE_GRAPH_STATE_FOR_PLANNING,
    SAMPLE_PLANNING_RESPONSE,
    EMPTY_PLANNING_RESPONSE,
    EMPTY_GRAPH_STATE_FOR_PLANNING,
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


class TestExtractInvestigationsSummary:
    """Test cases for _extract_investigations_summary function."""

    def test_extract_investigations_summary_with_investigations(self):
        """Test extraction with investigations present."""
        investigations = SAMPLE_GRAPH_STATE_FOR_PLANNING.investigations

        result = extract_investigations_summary(investigations)

        assert isinstance(result, str)
        assert "## Devices" in result
        assert "### 1. Device: `xrd-1`" in result
        assert "### 2. Device: `xrd-2`" in result
        assert "**Device Profile:**" in result
        assert "**Role:**" in result

    def test_extract_investigations_summary_with_empty_investigations(self):
        """Test extraction with no investigations."""
        result = extract_investigations_summary([])

        assert isinstance(result, str)
        assert "## Investigations" in result
        assert "No investigations defined." in result

    def test_extract_investigations_summary_structure(self):
        """Test that summary has proper markdown structure."""
        investigations = SAMPLE_GRAPH_STATE_FOR_PLANNING.investigations

        result = extract_investigations_summary(investigations)

        # Should have proper markdown headers
        lines = result.split("\n")
        assert any(line.startswith("##") for line in lines)
        assert any(line.startswith("###") for line in lines)
        assert any("```" in line for line in lines)

    def test_extract_investigations_summary_includes_device_profiles(self):
        """Test that device profiles are included in the summary."""
        investigations = SAMPLE_GRAPH_STATE_FOR_PLANNING.investigations

        result = extract_investigations_summary(investigations)

        # Check that device profiles are included
        for investigation in investigations:
            assert investigation.device_profile in result

    def test_extract_investigations_summary_includes_roles(self):
        """Test that device roles are included in the summary."""
        investigations = SAMPLE_GRAPH_STATE_FOR_PLANNING.investigations

        result = extract_investigations_summary(investigations)

        # Check that roles are included
        for investigation in investigations:
            assert f"**Role:** {investigation.role}" in result


class TestBuildSuccessfulPlanningState:
    """Test cases for _build_successful_planning_state function."""

    def test_build_successful_planning_state_updates_investigations(self):
        """Test that successful planning updates investigations with plan data."""
        result = build_successful_planning_state(
            SAMPLE_GRAPH_STATE_FOR_PLANNING, SAMPLE_PLANNING_RESPONSE
        )

        assert isinstance(result, GraphState)
        assert len(result.investigations) == len(
            SAMPLE_GRAPH_STATE_FOR_PLANNING.investigations
        )

        # Check that investigations are updated with planning data
        for investigation in result.investigations:
            if investigation.device_name == "xrd-1":
                assert (
                    investigation.objective
                    == "Check PE router health and MPLS status"
                )
                assert (
                    "Step 1: Check system info"
                    in investigation.working_plan_steps
                )
            elif investigation.device_name == "xrd-2":
                assert (
                    investigation.objective
                    == "Check P router health and core connectivity"
                )
                assert (
                    "Step 1: Check system info"
                    in investigation.working_plan_steps
                )

    def test_build_successful_planning_state_preserves_other_fields(self):
        """Test that successful planning preserves other state fields."""
        result = build_successful_planning_state(
            SAMPLE_GRAPH_STATE_FOR_PLANNING, SAMPLE_PLANNING_RESPONSE
        )

        assert (
            result.trigger_context
            == SAMPLE_GRAPH_STATE_FOR_PLANNING.trigger_context
        )

    def test_build_successful_planning_state_with_partial_plans(self):
        """Test planning with partial plans (not all devices have plans)."""
        partial_planning_response = PlanningResponse(
            plan=[
                DevicePlan(
                    device_name="xrd-1",
                    role="PE",
                    objective="Only first device planned",
                    working_plan_steps="Step 1: First device only",
                ),
                # Missing plan for xrd-2
            ]
        )

        result = build_successful_planning_state(
            SAMPLE_GRAPH_STATE_FOR_PLANNING, partial_planning_response
        )

        # First device should be updated
        first_investigation = next(
            inv for inv in result.investigations if inv.device_name == "xrd-1"
        )
        assert first_investigation.objective == "Only first device planned"

        # Second device should remain unchanged
        second_investigation = next(
            inv for inv in result.investigations if inv.device_name == "xrd-2"
        )
        assert second_investigation.objective is None

    def test_build_successful_planning_state_with_empty_plans(self):
        """Test planning with empty planning response."""
        result = build_successful_planning_state(
            SAMPLE_GRAPH_STATE_FOR_PLANNING, EMPTY_PLANNING_RESPONSE
        )

        # Investigations should remain unchanged
        for original, updated in zip(
            SAMPLE_GRAPH_STATE_FOR_PLANNING.investigations,
            result.investigations,
        ):
            assert updated.objective == original.objective
            assert updated.working_plan_steps == original.working_plan_steps

    def test_build_successful_planning_state_preserves_investigation_fields(
        self,
    ):
        """Test that planning preserves existing investigation fields."""
        result = build_successful_planning_state(
            SAMPLE_GRAPH_STATE_FOR_PLANNING, SAMPLE_PLANNING_RESPONSE
        )

        for original, updated in zip(
            SAMPLE_GRAPH_STATE_FOR_PLANNING.investigations,
            result.investigations,
        ):
            assert updated.device_name == original.device_name
            assert updated.device_profile == original.device_profile
            assert updated.role == original.role
            assert updated.status == original.status


class TestBuildFailedPlanningState:
    """Test cases for _build_failed_planning_state function."""

    def test_build_failed_planning_state_sets_error_info(self):
        """Test that failed planning sets error information on investigations."""
        result = build_failed_planning_state(
            SAMPLE_GRAPH_STATE_FOR_PLANNING, SAMPLE_PLANNING_ERROR
        )

        assert isinstance(result, GraphState)

        # All investigations should have error information
        for investigation in result.investigations:
            assert investigation.objective is not None
            assert "Planning Error" in investigation.objective
            assert (
                "Planning failed. Manual intervention required."
                in investigation.working_plan_steps
            )
            assert investigation.error_details is not None
            assert "Planning failed" in investigation.error_details

    def test_build_failed_planning_state_preserves_other_fields(self):
        """Test that failed planning preserves other state fields."""
        result = build_failed_planning_state(
            SAMPLE_GRAPH_STATE_FOR_PLANNING, SAMPLE_PLANNING_ERROR
        )

        assert (
            result.trigger_context
            == SAMPLE_GRAPH_STATE_FOR_PLANNING.trigger_context
        )

    def test_build_failed_planning_state_with_empty_investigations(self):
        """Test failed planning with empty investigations list."""
        result = build_failed_planning_state(
            EMPTY_GRAPH_STATE_FOR_PLANNING, SAMPLE_PLANNING_ERROR
        )

        assert len(result.investigations) == 0

    def test_build_failed_planning_state_preserves_investigation_structure(
        self,
    ):
        """Test that failed planning preserves investigation structure."""
        result = build_failed_planning_state(
            SAMPLE_GRAPH_STATE_FOR_PLANNING, SAMPLE_PLANNING_ERROR
        )

        for original, updated in zip(
            SAMPLE_GRAPH_STATE_FOR_PLANNING.investigations,
            result.investigations,
        ):
            assert updated.device_name == original.device_name
            assert updated.device_profile == original.device_profile
            assert updated.role == original.role
            assert updated.status == original.status


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
        assert plan.role == ""  # Default value

    def test_device_plan_with_role(self):
        """Test DevicePlan creation with role specified."""
        plan = DevicePlan(
            device_name="test-device",
            role="PE",
            objective="Test objective",
            working_plan_steps="Step 1: Test step",
        )

        assert plan.device_name == "test-device"
        assert plan.role == "PE"
        assert plan.objective == "Test objective"
        assert plan.working_plan_steps == "Step 1: Test step"


class TestPlanningResponseDataClass:
    """Test cases for PlanningResponse data class."""

    def test_planning_response_creation(self):
        """Test PlanningResponse creation."""
        response = PlanningResponse(
            plan=[
                DevicePlan(
                    device_name="device1",
                    objective="obj1",
                    working_plan_steps="steps1",
                ),
                DevicePlan(
                    device_name="device2",
                    objective="obj2",
                    working_plan_steps="steps2",
                ),
            ]
        )

        assert len(response) == 2
        assert len(response.plan) == 2

    def test_planning_response_len(self):
        """Test __len__ method of PlanningResponse."""
        response = SAMPLE_PLANNING_RESPONSE

        assert len(response) == len(response.plan)

    def test_planning_response_iter(self):
        """Test __iter__ method of PlanningResponse."""
        response = SAMPLE_PLANNING_RESPONSE

        plans_list = list(response)
        assert len(plans_list) == len(response.plan)

        for i, plan in enumerate(response):
            assert plan == response.plan[i]

    def test_planning_response_empty(self):
        """Test PlanningResponse with empty plan."""
        response = EMPTY_PLANNING_RESPONSE

        assert len(response) == 0
        assert list(response) == []
