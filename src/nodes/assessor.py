from dataclasses import replace

from langchain_core.messages import SystemMessage, HumanMessage

from util.llm import load_chat_model
from configuration import Configuration
from prompts.objective_assessor import OBJECTIVE_ASSESSOR_PROMPT
from schemas import GraphState, AssessmentOutput
from schemas.state import Investigation
from src.logging import get_logger, log_node_execution
from .markdown_builder import MarkdownBuilder

logger = get_logger(__name__)


@log_node_execution("Objective Assessor")
def objective_assessor_node(state: GraphState) -> GraphState:
    """
    Unified objective assessor node that evaluates all investigations and determines workflow completion.

    This function orchestrates the assessment workflow by:
    1. Building comprehensive context from all investigations
    2. Setting up the LLM model for assessment
    3. Generating assessment prompt and executing assessment
    4. Processing the assessment response
    5. Applying assessment decisions to update workflow state

    Args:
        state: The current workflow state containing user query, investigations, etc.

    Returns:
        Updated workflow state with the assessment results and next steps.
    """
    logger.info(
        "🔍 Assessing overall objective achievement for %d investigations",
        len(state.investigations),
    )

    try:
        assessment_context = _build_assessment_context(state)
        model = _setup_assessment_model()
        ai_assessment = _execute_assessment(model, assessment_context)
        return _apply_assessment_to_workflow(state, ai_assessment)

    except (ValueError, TypeError, AttributeError) as e:
        logger.error("❌ Assessment failed: %s", e)
        return _handle_assessment_error(state, e)
    except Exception as e:  # Catch all other unexpected errors
        logger.error("❌ Unexpected assessment error: %s", e)
        return _handle_assessment_error(state, e)


def _build_assessment_context(state: GraphState) -> str:
    """
    Build comprehensive assessment context from all investigations in markdown format.

    Args:
        state: Current workflow state

    Returns:
        Markdown-formatted context string for the LLM
    """
    logger.debug(
        "📋 Building assessment context for %d investigations",
        len(state.investigations),
    )

    builder = MarkdownBuilder()
    builder.add_header("Network Investigation Assessment Context")

    builder.add_section("User Query")
    builder.add_text(state.user_query)

    if state.current_retries > 0:
        builder.add_section("Retry Information")
        builder.add_bullet(
            f"Current attempt: {state.current_retries} of {state.max_retries}"
        )
        previous_feedback = (
            state.assessment.feedback_for_retry
            if state.assessment and state.assessment.feedback_for_retry
            else "No specific feedback provided"
        )
        builder.add_bullet(f"Previous feedback: {previous_feedback}")

    builder.add_section("Device Investigations")

    if not state.investigations:
        builder.add_text("No device investigations found.")
    else:
        for i, investigation in enumerate(state.investigations, 1):
            _add_investigation_to_builder(builder, investigation, i)

    _add_session_context_to_builder(builder, state.workflow_session)

    context_string = builder.build()
    logger.debug(
        "📤 Assessment context prepared (%d characters)", len(context_string)
    )
    return context_string


def _add_investigation_to_builder(
    builder: MarkdownBuilder, investigation: Investigation, index: int
) -> None:
    """
    Add individual investigation context to the markdown builder.

    Args:
        builder: Markdown builder instance
        investigation: Investigation object to format
        index: Investigation number for display
    """
    builder.add_subsection(
        f"Investigation {index}: {investigation.device_name}"
    )

    builder.add_bold_text("Status:", investigation.status.value)
    builder.add_bold_text(
        "Device Profile:", investigation.device_profile or "Not available"
    )
    builder.add_bold_text("Role:", investigation.role or "Not specified")
    builder.add_bold_text(
        "Objective:", investigation.objective or "Not specified"
    )

    builder.add_bold_text("Working Plan Steps:")
    builder.add_code_block(
        investigation.working_plan_steps or "No plan steps defined"
    )

    _add_execution_results_to_builder(builder, investigation.execution_results)

    if investigation.report:
        builder.add_bold_text("Investigation Report:")
        builder.add_code_block(investigation.report)

    if investigation.error_details:
        builder.add_bold_text("Error Details:", investigation.error_details)

    builder.add_separator()


def _add_session_context_to_builder(
    builder: MarkdownBuilder, workflow_session
) -> None:
    """
    Add workflow session context to the markdown builder.

    Args:
        builder: Markdown builder instance
        workflow_session: WorkflowSession object or None
    """
    builder.add_section("Workflow Session Context")

    if not workflow_session:
        builder.add_text("No previous workflow session context available.")
        return

    builder.add_bold_text("Session ID:", workflow_session.session_id)

    _add_previous_reports_to_builder(
        builder, workflow_session.previous_reports
    )
    _add_learned_patterns_to_builder(
        builder, workflow_session.learned_patterns
    )
    _add_device_relationships_to_builder(
        builder, workflow_session.device_relationships
    )


def _setup_assessment_model():
    """Setup and return the LLM model for objective assessment."""
    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)
    logger.debug("🤖 Using model for assessment: %s", configuration.model)
    return model


def _execute_assessment(model, assessment_context: str) -> AssessmentOutput:
    """
    Execute objective assessment using the LLM.

    Args:
        model: LLM model for structured output
        assessment_context: Prepared assessment context

    Returns:
        Assessment output from the LLM
    """
    logger.debug("🚀 Invoking LLM for objective assessment")

    messages = [
        SystemMessage(content=OBJECTIVE_ASSESSOR_PROMPT),
        HumanMessage(content=assessment_context),
    ]

    ai_response = model.with_structured_output(schema=AssessmentOutput).invoke(
        input=messages
    )

    logger.debug("📋 Structured output captured: %s", ai_response)

    assessment = _ensure_proper_assessment_format(ai_response)

    logger.debug(
        "📨 Assessment completed: is_objective_achieved=%s",
        assessment.is_objective_achieved,
    )
    return assessment


def _ensure_proper_assessment_format(ai_response) -> AssessmentOutput:
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


def _add_execution_results_to_builder(
    builder: MarkdownBuilder, execution_results
) -> None:
    """
    Add execution results to the markdown builder.

    Args:
        builder: Markdown builder instance
        execution_results: List of execution results
    """
    if execution_results:
        builder.add_bold_text(
            "Execution Results:",
            f"{len(execution_results)} tool calls executed",
        )
        for j, result in enumerate(execution_results, 1):
            builder.add_bold_text(f"Tool Call {j}:", result.function)
            builder.add_bullet(f"Parameters: {result.params}")
            builder.add_bullet(f"Error: {result.error or 'None'}")

            # Add the full result content as JSON if available
            if result.result:
                builder.add_bold_text("Result:")
                builder.add_code_block(str(result))
            else:
                builder.add_bullet("Result: Not available")

            builder.add_empty_line()
    else:
        builder.add_bold_text(
            "Execution Results:", "No execution results available"
        )


def _add_previous_reports_to_builder(
    builder: MarkdownBuilder, previous_reports
) -> None:
    """
    Add previous reports to the markdown builder.

    Args:
        builder: Markdown builder instance
        previous_reports: List of previous reports
    """
    if previous_reports:
        builder.add_bold_text(
            "Previous Reports:", f"{len(previous_reports)} available"
        )
        for i, report in enumerate(previous_reports, 1):
            builder.add_bold_text(f"Report {i}:")
            builder.add_code_block(report)
    else:
        builder.add_bold_text(
            "Previous Reports:", "No previous reports available"
        )


def _add_learned_patterns_to_builder(
    builder: MarkdownBuilder, learned_patterns
) -> None:
    """
    Add learned patterns to the markdown builder.

    Args:
        builder: Markdown builder instance
        learned_patterns: Dictionary of learned patterns
    """
    if learned_patterns:
        builder.add_bold_text(
            "Learned Patterns:", f"{len(learned_patterns)} patterns available"
        )
        for pattern_name, pattern_data in learned_patterns.items():
            builder.add_bullet(f"**{pattern_name}:** {pattern_data}")
        builder.add_empty_line()
    else:
        builder.add_bold_text(
            "Learned Patterns:", "No learned patterns available"
        )


def _add_device_relationships_to_builder(
    builder: MarkdownBuilder, device_relationships
) -> None:
    """
    Add device relationships to the markdown builder.

    Args:
        builder: Markdown builder instance
        device_relationships: Dictionary of device relationships
    """
    if device_relationships:
        builder.add_bold_text(
            "Device Relationships:",
            f"{len(device_relationships)} relationships available",
        )
        for device, relationships in device_relationships.items():
            builder.add_bullet(f"**{device}:** {', '.join(relationships)}")
        builder.add_empty_line()
    else:
        builder.add_bold_text(
            "Device Relationships:", "No device relationships available"
        )
