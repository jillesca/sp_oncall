import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field


@dataclass
class MultiInvestigationAssessmentOutput:
    """
    Structured output schema for multi-investigation assessment.

    Attributes:
        overall_objective_achieved: True if the user's original query is satisfied
            across all investigations. False if retry or additional work is needed.
        investigation_success_rate: Ratio (0.0-1.0) of successful investigations.
        critical_issues: List of major problems requiring attention.
        notes_for_final_report: Comprehensive assessment summary.
        feedback_for_retry: Specific guidance if retry needed, null otherwise.
        learned_patterns: Patterns discovered for future investigations.
    """

    overall_objective_achieved: bool
    investigation_success_rate: float
    critical_issues: List[str] = field(default_factory=list)
    notes_for_final_report: str = ""
    feedback_for_retry: Optional[str] = None
    learned_patterns: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """Return a JSON representation of the multi-investigation assessment output."""
        return json.dumps(asdict(self), indent=2, default=str)

    def __repr__(self) -> str:
        """Return a detailed representation for debugging."""
        return f"MultiInvestigationAssessmentOutput(achieved={self.overall_objective_achieved}, success_rate={self.investigation_success_rate:.2f})"


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
