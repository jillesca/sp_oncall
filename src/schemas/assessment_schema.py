import json
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class AssessmentOutput:
    """
    Structured output schema for the objective assessor node.

    Attributes:
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
    feedback_for_retry: Optional[str] = None

    def __str__(self) -> str:
        """Return a JSON representation of the assessment output."""
        return json.dumps(asdict(self), indent=2, default=str)

    def __repr__(self) -> str:
        """Return a detailed representation for debugging."""
        return f"AssessmentOutput(is_objective_achieved={self.is_objective_achieved}, notes='{self.notes_for_final_report[:50]}...')"
