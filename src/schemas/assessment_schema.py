from typing import Optional, TypedDict


class AssessmentOutput(TypedDict):
    """
    Structured output schema for the objective assessor node.
    Fields:
        is_objective_achieved: True if the objective is met or cannot be further
            improved due to limitations. False if the objective is not met and
            a retry is feasible.

        notes_for_final_report: A concise summary of the assessment (e.g.,
            "Objective successfully met.", "Objective partially met; some data
            unavailable due to tool errors.", "Objective not met; critical
            information missing.").

        feedback_for_retry: If is_objective_achieved is False, provides specific,
            actionable feedback for the Network Executor's next attempt. This feedback
            should guide the executor on what to do differently or what to focus on.
            If is_objective_achieved is True, or if no retry is useful, this will be None.
    """

    is_objective_achieved: bool
    notes_for_final_report: str
    feedback_for_retry: Optional[str]
