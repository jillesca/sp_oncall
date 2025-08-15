import json
from typing import List
from dataclasses import dataclass, asdict, field


@dataclass
class PlannerOutput:
    """
    Structured output schema for the planner node.

    Attributes:
        objective: The main objective determined by the planner.
        steps: List of plan steps to execute for achieving the objective.
    """

    objective: str
    steps: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        """Return a JSON representation of the planner output."""
        return json.dumps(asdict(self), indent=2, default=str)

    def __repr__(self) -> str:
        """Return a detailed representation for debugging."""
        return f"PlannerOutput(objective='{self.objective[:50]}...', steps={len(self.steps)} steps)"
