"""Define the state structures for the agent.

This module centralizes the shared workflow state and structured outputs used
by the LangGraph nodes. Each dataclass includes a concise docstring with field
descriptions to keep the code readable and self-explanatory.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class GraphState:
    """Shared workflow state passed between LangGraph nodes.

    Attributes:
        user_query: The original user question or task description.
        device_name: The target device extracted/resolved from the user query.
        objective: The current objective determined by validation/planning.
        working_plan_steps: Ordered list of plan steps to execute.
        execution_results: Collected results for each executed plan step.

        max_retries: Upper bound of the assessor-guided retry loop.
        current_retries: Current retry attempt count.
        objective_achieved_assessment: Assessment from the objective assessor
            indicating whether the objective has been met (True), needs retry (False),
            or is not yet decided (None).
        assessor_feedback_for_retry: Concrete guidance for the executor to use
            on the next retry.
        assessor_notes_for_final_report: Notes the assessor wants included in
            the final report.

        summary: Final synthesized summary/report once the workflow completes.
    """

    user_query: str
    device_name: str = ""
    objective: str = ""
    working_plan_steps: List[str] = field(default_factory=list)
    execution_results: List[StepExecutionResult] = field(default_factory=list)

    max_retries: int = 3
    current_retries: int = 0
    objective_achieved_assessment: Optional[bool] = None
    assessor_feedback_for_retry: Optional[str] = None
    assessor_notes_for_final_report: Optional[str] = None

    summary: Optional[str] = None

    def __str__(self) -> str:
        """Return a JSON representation of the graph state."""
        return json.dumps(asdict(self), indent=2, default=str)

    def __repr__(self) -> str:
        """Return a detailed representation for debugging."""
        return (
            f"GraphState(user_query='{self.user_query[:50]}...', "
            f"device_name='{self.device_name}', "
            f"objective='{self.objective[:50]}...', "
            f"execution_results={len(self.execution_results)} results)"
        )


@dataclass
class StepExecutionResult:
    """Outcome of executing a single natural-language plan step.

    Attributes:
        investigation_report: Narrative report produced by the LLM for this step.
        executed_calls: Sequence of concrete tool calls performed for this step.
    """

    investigation_report: str
    executed_calls: List[ExecutedToolCall] = field(default_factory=list)

    def __str__(self) -> str:
        """Return a JSON representation of the step execution result."""
        return json.dumps(asdict(self), indent=2, default=str)

    def __repr__(self) -> str:
        """Return a detailed representation for debugging."""
        return f"StepExecutionResult(investigation_report='{self.investigation_report[:50]}...', executed_calls={len(self.executed_calls)} calls)"


@dataclass
class ExecutedToolCall:
    """Details of a single tool invocation made by the executor LLM.

    Attributes:
        function: Name of the tool invoked (e.g., "get_routing_info").
        params: Parameters passed to the tool.
        result: Structured result returned by the tool, if successful.
        error: Error message if the tool invocation failed.
        detailed_findings: Free-form details gathered during this call.
    """

    function: str
    params: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    detailed_findings: str = ""

    def __str__(self) -> str:
        """Return a JSON representation of the tool call."""
        return json.dumps(asdict(self), indent=2, default=str)

    def __repr__(self) -> str:
        """Return a detailed representation for debugging."""
        return f"ExecutedToolCall(function='{self.function}', params={self.params}, error={self.error})"
