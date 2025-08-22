"""
State management for assessment workflow.

This module handles applying assessment decisions to update workflow state,
including success scenarios, retry logic, and error handling.
"""

from dataclasses import replace

from schemas import GraphState, AssessmentOutput
from src.logging import get_logger

logger = get_logger(__name__)


def apply_assessment_to_workflow(
    state: GraphState, assessment: AssessmentOutput
) -> GraphState:
    """
    Apply assessment decision to update the workflow state.

    Args:
        state: Current workflow state
        assessment: Assessment results from the LLM

    Returns:
        Updated workflow state based on assessment
    """
    if assessment.is_objective_achieved:
        return _build_successful_assessment_state(state, assessment)
    else:
        return _build_retry_or_failed_assessment_state(state, assessment)


def handle_assessment_error(state: GraphState, error: Exception) -> GraphState:
    """
    Handle assessment errors by updating the workflow appropriately.

    Args:
        state: Current workflow state
        error: Exception that occurred during assessment

    Returns:
        Updated workflow state with error handling
    """
    logger.debug("🚨 Handling assessment error: %s", error)

    if state.current_retries < state.max_retries:
        return _build_error_retry_state(state, error)
    else:
        return _build_error_final_state(state, error)


def _build_successful_assessment_state(
    state: GraphState, assessment: AssessmentOutput
) -> GraphState:
    """
    Build workflow state for successful objective achievement.

    Args:
        state: Current workflow state
        assessment: Assessment results

    Returns:
        Updated state for successful completion
    """
    logger.info("✅ Objective has been achieved")

    return replace(
        state,
        assessment=assessment,
    )


def _build_retry_or_failed_assessment_state(
    state: GraphState, assessment: AssessmentOutput
) -> GraphState:
    """
    Build workflow state for retry or final failure.

    Args:
        state: Current workflow state
        assessment: Assessment results

    Returns:
        Updated state for retry attempt or final failure
    """
    logger.warning("❌ Objective not yet achieved")

    if state.current_retries < state.max_retries:
        return _build_retry_state(state, assessment)
    else:
        return _build_max_retries_reached_state(state, assessment)


def _build_retry_state(
    state: GraphState, assessment: AssessmentOutput
) -> GraphState:
    """
    Build workflow state for retry attempt.

    Args:
        state: Current workflow state
        assessment: Assessment results

    Returns:
        Updated state for retry attempt
    """
    logger.debug(
        "🔄 Preparing for retry attempt %s", state.current_retries + 1
    )

    feedback = (
        assessment.feedback_for_retry or _get_encouraging_retry_guidance()
    )

    # Create updated assessment with retry feedback
    retry_assessment = replace(
        assessment,
        feedback_for_retry=feedback,
    )

    return replace(
        state,
        assessment=retry_assessment,
        current_retries=state.current_retries + 1,
    )


def _build_max_retries_reached_state(
    state: GraphState, assessment: AssessmentOutput
) -> GraphState:
    """
    Build workflow state when maximum retries are reached.

    Args:
        state: Current workflow state
        assessment: Assessment results

    Returns:
        Updated state for final completion
    """
    logger.warning("🚫 Maximum attempts reached, forcing completion")

    final_notes = (
        f"Objective not achieved after {state.max_retries} attempts. "
        f"{assessment.notes_for_final_report}"
    )

    # Create final assessment marking as achieved to stop retry loop
    final_assessment = replace(
        assessment,
        is_objective_achieved=True,  # Stop the retry loop
        notes_for_final_report=final_notes,
        feedback_for_retry=None,
    )

    return replace(
        state,
        assessment=final_assessment,
    )


def _build_error_retry_state(
    state: GraphState, error: Exception
) -> GraphState:
    """
    Build workflow state for error with retry available.

    Args:
        state: Current workflow state
        error: Exception that occurred

    Returns:
        Updated state for error retry
    """
    logger.debug("🔄 Error occurred, but retries available")

    error_assessment = AssessmentOutput(
        is_objective_achieved=False,
        notes_for_final_report=f"Assessment encountered an error: {error}. Will attempt retry.",
        feedback_for_retry="An unexpected error occurred during assessment. Please try a different approach.",
    )

    return replace(
        state,
        assessment=error_assessment,
        current_retries=state.current_retries + 1,
    )


def _build_error_final_state(
    state: GraphState, error: Exception
) -> GraphState:
    """
    Build workflow state for error with no retries remaining.

    Args:
        state: Current workflow state
        error: Exception that occurred

    Returns:
        Updated state for final error completion
    """
    logger.debug("🚫 Error occurred with no retries remaining")

    final_error_assessment = AssessmentOutput(
        is_objective_achieved=True,  # Force completion
        notes_for_final_report=f"Assessment error after maximum attempts: {error}. Process concluded.",
        feedback_for_retry=None,
    )

    return replace(
        state,
        assessment=final_error_assessment,
    )


def _get_encouraging_retry_guidance() -> str:
    """Provides helpful guidance when AI doesn't give specific retry feedback."""
    return (
        "The AI assessment didn't provide specific guidance for improvement. "
        "Please carefully review what was accomplished against the original request, "
        "then try a different approach, focusing on any gaps or areas that seem incomplete."
    )
