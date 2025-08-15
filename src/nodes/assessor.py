import json
from dataclasses import replace
from typing import Dict, Any, Optional

from langchain_core.messages import SystemMessage

from util.llm import load_chat_model
from util.utils import serialize_for_prompt
from configuration import Configuration
from schemas import GraphState, AssessmentOutput, StepExecutionResult
from prompts.objective_assessor import OBJECTIVE_ASSESSOR_PROMPT


def objective_assessor_node(
    state: GraphState,
) -> GraphState:
    """
    Assesses if the execution results meet the objective, handles retries, and provides feedback.

    This function evaluates whether the execution results from the network executor
    successfully satisfy the user's query.

    Args:
        state: The current GraphState.

    Returns:
        Updated GraphState with assessment results.
    """
    state_values = extract_state_values(state)

    assessment_result = perform_assessment(state_values)

    return replace(
        state,
        objective_achieved_assessment=assessment_result["objective_achieved"],
        assessor_notes_for_final_report=assessment_result["notes_for_report"],
        assessor_feedback_for_retry=assessment_result["feedback_for_retry"],
        current_retries=assessment_result["current_retries"],
    )


def extract_state_values(state: GraphState) -> Dict[str, Any]:
    """Extracts and provides default values for necessary state components."""
    execution_results = state.execution_results
    if not execution_results:
        execution_results = [
            StepExecutionResult(
                investigation_report="Execution results not found",
                executed_calls=[],
                tools_limitations="Execution results not found",
            )
        ]

    return {
        "user_query": state.user_query or "User query not available",
        "objective": state.objective or "Objective not available",
        "working_plan_steps": state.working_plan_steps,
        "execution_results": execution_results,
        "current_retries": state.current_retries,
        "max_retries": state.max_retries,
    }


def perform_assessment(state_values: Dict[str, Any]) -> Dict[str, Any]:
    """Performs the assessment using the LLM and handles retry logic."""

    try:
        response = get_llm_assessment(state_values)
        return process_assessment_response(response, state_values)
    except (
        Exception
    ) as e:  # Broad exception is intentional for fallback handling
        return handle_assessment_error(e, state_values)


def get_llm_assessment(state_values: Dict[str, Any]) -> Any:
    """Gets the assessment from the LLM."""

    context = {
        "user_query": state_values["user_query"],
        "objective": serialize_for_prompt(state_values["objective"]),
        "working_plan_steps": serialize_for_prompt(
            state_values["working_plan_steps"]
        ),
        "execution_results": serialize_for_prompt(
            state_values["execution_results"]
        ),
    }

    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)

    system_message = OBJECTIVE_ASSESSOR_PROMPT.format(**context)
    return model.with_structured_output(AssessmentOutput).invoke(
        [
            SystemMessage(content=system_message),
        ]
    )


def process_assessment_response(
    response: AssessmentOutput, state_values: Dict[str, Any]
) -> Dict[str, Any]:
    """Processes the LLM assessment response and handles retry logic."""
    objective_achieved = response.get("is_objective_achieved", False)
    notes_for_report = response.get(
        "notes_for_final_report",
        "Assessment incomplete. The Assessor model did not provide a proper assessment.",
    )
    feedback_for_retry = response.get(
        "feedback_for_retry",
        "No feedback for retry provided by the Assessor model. The objective was not fully met. Please review the execution results against the objective and plan steps, then try again, focusing on any identified gaps or inconsistencies.",
    )

    if not objective_achieved:
        return handle_unmet_objective(
            state_values["current_retries"],
            state_values["max_retries"],
            notes_for_report,
            feedback_for_retry,
        )

    return {
        "objective_achieved": True,
        "notes_for_report": notes_for_report,
        "feedback_for_retry": None,
        "current_retries": state_values["current_retries"],
    }


def handle_unmet_objective(
    current_retries: int,
    max_retries: int,
    notes_for_report: str,
    feedback_for_retry: Optional[str],
) -> Dict[str, Any]:
    """Handles the case when the objective is not met."""
    if current_retries < max_retries:
        current_retries += 1

        return {
            "objective_achieved": False,
            "notes_for_report": notes_for_report,
            "feedback_for_retry": feedback_for_retry,
            "current_retries": current_retries,
        }

    return {
        "objective_achieved": True,
        "notes_for_report": (
            f"Objective not met after {max_retries} retries. {notes_for_report or 'No specific additional notes from assessor for max retries.'}"
        ),
        "feedback_for_retry": None,
        "current_retries": current_retries,
    }


def handle_assessment_error(
    error: Exception, state_values: Dict[str, Any]
) -> Dict[str, Any]:
    """Handles errors during assessment."""
    if state_values["current_retries"] < state_values["max_retries"]:
        state_values["current_retries"] += 1

        return {
            "objective_achieved": False,
            "notes_for_report": f"Error in assessment: {error}. Attempting retry.",
            "feedback_for_retry": "An error occurred during assessment. Please re-evaluate the objective.",
            "current_retries": state_values["current_retries"],
        }

    # Max retries reached, force completion
    return {
        "objective_achieved": True,  # Stop retrying
        "notes_for_report": f"Error in assessment: {error}. Max retries reached.",
        "feedback_for_retry": None,
        "current_retries": state_values["current_retries"],
    }
