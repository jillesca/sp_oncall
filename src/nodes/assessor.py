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

    Args:
        state: The current workflow state containing user query, execution results, etc.

    Returns:
        Updated workflow state with the assessment results and next steps.
    """
    logger.info("🔍 Assessing objective achievement for: %s", state.objective)

    assessment_teacher = NetworkObjectiveAssessmentTeacher(state)

    return assessment_teacher.evaluate_and_update_workflow()


class NetworkObjectiveAssessmentTeacher:
    """
    Evaluates whether network investigation results meet user objectives.
    """

    def __init__(self, workflow_state: GraphState):
        self.workflow_state = workflow_state

    def evaluate_and_update_workflow(self) -> GraphState:
        """
        Evaluates the network execution results and returns an updated workflow state.
        """
        try:
            logger.debug("Starting AI assessment of network execution")
            ai_assessment = self._get_ai_assessment_of_network_execution()
            return self._apply_assessment_decision_to_workflow(ai_assessment)

        except Exception as assessment_error:
            logger.error("Assessment failed: %s", assessment_error)
            return self._handle_assessment_error_in_workflow(assessment_error)

    def _get_ai_assessment_of_network_execution(self) -> AssessmentOutput:
        """
        Asks the AI model to assess whether the network execution met the objectives.
        """
        logger.debug("Preparing prompt information for AI assessment")

        # Prepare information for the AI prompt using the workflow state directly
        prompt_information = {
            "user_query": self.workflow_state.user_query
            or "User question not available",
            "objective": serialize_for_prompt(
                self.workflow_state.objective or "Objective not available"
            ),
            "working_plan_steps": serialize_for_prompt(
                self.workflow_state.working_plan_steps or []
            ),
            "execution_results": serialize_for_prompt(
                self._get_execution_results_with_fallback()
            ),
        }

        # Get AI model and make the assessment request
        configuration = Configuration.from_context()
        ai_model = load_chat_model(configuration.model)
        logger.debug("Using model for assessment: %s", configuration.model)

        logger.debug("Invoking LLM for objective assessment")
        formatted_prompt = OBJECTIVE_ASSESSOR_PROMPT.format(
            **prompt_information
        )
        ai_response = ai_model.with_structured_output(
            schema=AssessmentOutput
        ).invoke(input=[SystemMessage(content=formatted_prompt)])

        # Ensure we have a proper AssessmentOutput object
        assessment = self._ensure_proper_assessment_format(ai_response)
        logger.debug(
            f"Assessment completed: is_objective_achieved={assessment.is_objective_achieved}"
        )
        return assessment

    def _get_execution_results_with_fallback(
        self,
    ) -> List[StepExecutionResult]:
        """Provides execution results with a sensible fallback if none exist."""
        if self.workflow_state.execution_results:
            return self.workflow_state.execution_results

        return [
            StepExecutionResult(
                investigation_report="No network execution results were found",
                executed_calls=[],
                tools_limitations="Network execution results are missing",
            )
        ]

    def _ensure_proper_assessment_format(
        self, ai_response: Any
    ) -> AssessmentOutput:
        """
        Ensures the AI's response is in a reliable format we can work with.
        """
        if isinstance(ai_response, AssessmentOutput):
            return ai_response

        if isinstance(ai_response, dict):
            # Convert dictionary response to proper object
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

    def _apply_assessment_decision_to_workflow(
        self, ai_assessment: AssessmentOutput
    ) -> GraphState:
        """
        Applies the assessment decision directly to the workflow state.
        """
        if ai_assessment.is_objective_achieved:
            logger.info("✅ Objective has been achieved")
            # Success! Update workflow to reflect completion
            return replace(
                self.workflow_state,
                objective_achieved_assessment=True,
                assessor_notes_for_final_report=ai_assessment.notes_for_final_report,
                assessor_feedback_for_retry=None,
                # Keep current retries as-is for successful completion
            )

        logger.warning("❌ Objective not yet achieved")
        # Objective not achieved - decide whether to retry or stop
        if (
            self.workflow_state.current_retries
            < self.workflow_state.max_retries
        ):
            # We can try again - encourage another attempt
            return replace(
                self.workflow_state,
                objective_achieved_assessment=False,
                assessor_notes_for_final_report=ai_assessment.notes_for_final_report,
                assessor_feedback_for_retry=ai_assessment.feedback_for_retry
                or self._get_encouraging_retry_guidance(),
                current_retries=self.workflow_state.current_retries + 1,
            )

        # Maximum attempts reached - force completion
        return replace(
            self.workflow_state,
            objective_achieved_assessment=True,  # Stop the retry loop
            assessor_notes_for_final_report=(
                f"Objective not achieved after {self.workflow_state.max_retries} attempts. "
                f"{ai_assessment.notes_for_final_report}"
            ),
            assessor_feedback_for_retry=None,
            # Keep current retries as-is since we're stopping
        )

    def _get_encouraging_retry_guidance(self) -> str:
        """Provides helpful guidance when AI doesn't give specific retry feedback."""
        return (
            "The AI assessment didn't provide specific guidance for improvement. "
            "Please carefully review what was accomplished against the original request, "
            "then try a different approach, focusing on any gaps or areas that seem incomplete."
        )

    def _handle_assessment_error_in_workflow(
        self, assessment_error: Exception
    ) -> GraphState:
        """
        Gracefully handles assessment errors by updating the workflow appropriately.
        """
        if (
            self.workflow_state.current_retries
            < self.workflow_state.max_retries
        ):
            # We can retry after an error
            return replace(
                self.workflow_state,
                objective_achieved_assessment=False,
                assessor_notes_for_final_report=f"Assessment encountered an error: {assessment_error}. Will attempt retry.",
                assessor_feedback_for_retry="An unexpected error occurred during assessment. Please try a different approach.",
                current_retries=self.workflow_state.current_retries + 1,
            )

        # No more retries available - conclude with error
        return replace(
            self.workflow_state,
            objective_achieved_assessment=True,  # Force completion
            assessor_notes_for_final_report=f"Assessment error after maximum attempts: {assessment_error}. Process concluded.",
            assessor_feedback_for_retry=None,
            # Keep current retries as-is
        )
