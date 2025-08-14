"""Define the state structures for the agent.

This module centralizes the shared workflow state and structured outputs used
by the LangGraph nodes. Each TypedDict includes a concise docstring with field
descriptions to keep the code readable and self-explanatory.
"""

from __future__ import annotations

from typing import TypedDict, List, Dict, Any, Optional


class ExecutedToolCall(TypedDict):
    """Details of a single tool invocation made by the executor LLM.

    Keys:
        function: Name of the tool invoked (e.g., "get_routing_info").
        params: Parameters passed to the tool.
        result: Structured result returned by the tool, if successful.
        error: Error message if the tool invocation failed.
        detailed_findings: Free-form details gathered during this call.
    """

    function: str
    params: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    detailed_findings: str


class StepExecutionResult(TypedDict):
    """Outcome of executing a single natural-language plan step.

    Keys:
        investigation_report: Narrative report produced by the LLM for this step.
        tools_limitations: Any limitations or constraints encountered.
        executed_calls: Sequence of concrete tool calls performed for this step.
    """

    investigation_report: str
    tools_limitations: str
    executed_calls: List[ExecutedToolCall]


class GraphState(TypedDict):
    """Shared workflow state passed between LangGraph nodes.

    Keys:
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
    device_name: str
    objective: str
    working_plan_steps: List[str]
    execution_results: List[StepExecutionResult]

    max_retries: int
    current_retries: int
    objective_achieved_assessment: Optional[bool]
    assessor_feedback_for_retry: Optional[str]
    assessor_notes_for_final_report: Optional[str]

    summary: Optional[str]
