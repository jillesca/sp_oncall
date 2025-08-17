from dataclasses import replace
from typing import Any, List

from langchain_core.messages import SystemMessage

from util.llm import load_chat_model
from configuration import Configuration
from util.utils import serialize_for_prompt
from prompts.objective_assessor import OBJECTIVE_ASSESSOR_PROMPT
from schemas import GraphState, AssessmentOutput, StepExecutionResult

# Add logging
from src.logging import get_logger, log_node_execution

logger = get_logger(__name__)


@log_node_execution("Objective Assessor")
def objective_assessor_node(state: GraphState) -> GraphState:
    """
    Determines whether the network execution results successfully fulfill the user's request.

    This function orchestrates the assessment workflow by:
    1. Preparing assessment data from the current state
    2. Setting up the LLM model for assessment
    3. Generating assessment prompts and executing assessment
    4. Processing the assessment response
    5. Applying assessment decisions to update workflow state

    Args:
        state: The current workflow state containing user query, execution results, etc.

    Returns:
        Updated workflow state with the assessment results and next steps.
    """
    logger.info("🔍 Assessing objective achievement for: %s", state.objective)

    try:
        assessment_data = _prepare_assessment_data(state)
        model = _setup_assessment_model()
        ai_assessment = _execute_objective_assessment(model, assessment_data)
        return _apply_assessment_to_workflow(state, ai_assessment)

    except Exception as e:
        logger.error("❌ Assessment failed: %s", e)
        return _handle_assessment_error(state, e)


def _prepare_assessment_data(state: GraphState) -> dict:
    """
    Prepare assessment data from the workflow state.

    Args:
        state: Current workflow state

    Returns:
        Dictionary containing assessment prompt information
    """
    logger.debug("📋 Preparing prompt information for AI assessment")

    execution_results = _get_execution_results_with_fallback(state)

    prompt_information = {
        "user_query": state.user_query or "User question not available",
        "objective": serialize_for_prompt(
            state.objective or "Objective not available"
        ),
        "working_plan_steps": serialize_for_prompt(
            state.working_plan_steps or []
        ),
        "execution_results": serialize_for_prompt(execution_results),
    }

    logger.debug("📤 Assessment data prepared")
    return prompt_information


def _get_execution_results_with_fallback(
    state: GraphState,
) -> List[StepExecutionResult]:
    """
    Provides execution results with a sensible fallback if none exist.

    Args:
        state: Current workflow state

    Returns:
        List of execution results or fallback data
    """
    if state.execution_results:
        return state.execution_results

    return [
        StepExecutionResult(
            investigation_report="No network execution results were found",
            executed_calls=[],
            tools_limitations="Network execution results are missing",
        )
    ]


def _setup_assessment_model():
    """Setup and return the LLM model for objective assessment."""
    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)
    logger.debug("🤖 Using model for assessment: %s", configuration.model)
    return model


def _execute_objective_assessment(
    model, assessment_data: dict
) -> AssessmentOutput:
    """
    Execute objective assessment using the LLM.

    Args:
        model: LLM model for structured output
        assessment_data: Prepared assessment data

    Returns:
        Assessment output from the LLM
    """
    logger.debug("🚀 Invoking LLM for objective assessment")

    formatted_prompt = OBJECTIVE_ASSESSOR_PROMPT.format(**assessment_data)
    ai_response = model.with_structured_output(schema=AssessmentOutput).invoke(
        input=[SystemMessage(content=formatted_prompt)]
    )

    assessment = _ensure_proper_assessment_format(ai_response)

    logger.debug(
        "📨 Assessment completed: is_objective_achieved=%s",
        assessment.is_objective_achieved,
    )
    return assessment


def _ensure_proper_assessment_format(ai_response: Any) -> AssessmentOutput:
    """
    Ensures the AI's response is in a reliable format we can work with.

    Args:
        ai_response: Raw response from the LLM

    Returns:
        Properly formatted AssessmentOutput
    """
    if isinstance(ai_response, AssessmentOutput):
        return ai_response

    if isinstance(ai_response, dict):
        return AssessmentOutput(
            is_objective_achieved=ai_response.get(
                "is_objective_achieved", False
            ),
            notes_for_final_report=ai_response.get(
                "notes_for_final_report",
                "Assessment incomplete. AI response could not be properly interpreted.",
            ),
            feedback_for_retry=ai_response.get("feedback_for_retry"),
        )

    # Handle completely unexpected response types
    return AssessmentOutput(
        is_objective_achieved=False,
        notes_for_final_report=f"Assessment failed. AI returned unexpected response type: {type(ai_response)}",
        feedback_for_retry="Unable to assess due to unexpected AI response format. Please try again.",
    )


def _apply_assessment_to_workflow(
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
        objective_achieved_assessment=True,
        assessor_notes_for_final_report=assessment.notes_for_final_report,
        assessor_feedback_for_retry=None,
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

    return replace(
        state,
        objective_achieved_assessment=False,
        assessor_notes_for_final_report=assessment.notes_for_final_report,
        assessor_feedback_for_retry=feedback,
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

    return replace(
        state,
        objective_achieved_assessment=True,  # Stop the retry loop
        assessor_notes_for_final_report=final_notes,
        assessor_feedback_for_retry=None,
    )


def _get_encouraging_retry_guidance() -> str:
    """Provides helpful guidance when AI doesn't give specific retry feedback."""
    return (
        "The AI assessment didn't provide specific guidance for improvement. "
        "Please carefully review what was accomplished against the original request, "
        "then try a different approach, focusing on any gaps or areas that seem incomplete."
    )


def _handle_assessment_error(
    state: GraphState, error: Exception
) -> GraphState:
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

    return replace(
        state,
        objective_achieved_assessment=False,
        assessor_notes_for_final_report=f"Assessment encountered an error: {error}. Will attempt retry.",
        assessor_feedback_for_retry="An unexpected error occurred during assessment. Please try a different approach.",
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

    return replace(
        state,
        objective_achieved_assessment=True,  # Force completion
        assessor_notes_for_final_report=f"Assessment error after maximum attempts: {error}. Process concluded.",
        assessor_feedback_for_retry=None,
    )
