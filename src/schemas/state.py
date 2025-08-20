"""
Define the state structures for the agent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Any, Optional


@dataclass
class GraphState:
    """Enhanced workflow state supporting multi-device investigations.

    Attributes:
        user_query: Original user question or task description.
        investigations: Collection of device-specific investigations.
        workflow_session: Historical context and learned patterns.

        # Global workflow control
        max_retries: Maximum retry attempts per investigation.
        current_retries: Global retry counter for the entire workflow.

        # Global assessment state
        overall_objective_achieved: Whether the user's overall query is satisfied.
        assessor_feedback_for_retry: Global feedback for workflow retry.
        assessor_notes_for_final_report: Notes for the comprehensive final report.

        # Final output
        final_report: Comprehensive report combining all investigations.
    """

    user_query: str
    investigations: List[Investigation] = field(default_factory=list)
    workflow_session: Optional[WorkflowSession] = None

    # Global workflow control
    max_retries: int = 3
    current_retries: int = 0

    # Global assessment state
    overall_objective_achieved: Optional[bool] = None
    assessor_feedback_for_retry: Optional[str] = None
    assessor_notes_for_final_report: Optional[str] = None

    # Final output
    final_report: Optional[str] = None

    def get_investigation_by_device(
        self, device_name: str
    ) -> Optional[Investigation]:
        """Retrieve investigation for a specific device."""
        return next(
            (
                inv
                for inv in self.investigations
                if inv.device_name == device_name
            ),
            None,
        )

    def get_pending_investigations(self) -> List[Investigation]:
        """Get investigations that haven't been started."""
        return [
            inv
            for inv in self.investigations
            if inv.status == InvestigationStatus.PENDING
        ]

    def get_ready_investigations(self) -> List[Investigation]:
        """Get investigations ready to execute (no unmet dependencies)."""
        completed_devices = {
            inv.device_name
            for inv in self.investigations
            if inv.status == InvestigationStatus.COMPLETED
        }

        return [
            inv
            for inv in self.investigations
            if inv.status == InvestigationStatus.PENDING
            and all(dep in completed_devices for dep in inv.dependencies)
        ]

    def all_investigations_complete(self) -> bool:
        """Check if all investigations have reached a terminal state."""
        terminal_statuses = {
            InvestigationStatus.COMPLETED,
            InvestigationStatus.FAILED,
            InvestigationStatus.SKIPPED,
        }
        return all(
            inv.status in terminal_statuses for inv in self.investigations
        )

    def __str__(self) -> str:
        """Return a JSON representation of the graph state."""
        return json.dumps(asdict(self), indent=2, default=str)


@dataclass
class WorkflowSession:
    """Represents the context and history from previous workflow sessions.

    Attributes:
        session_id: Unique identifier for this workflow session.
        previous_reports: Historical investigation reports for context.
        learned_patterns: Patterns discovered from previous investigations.
        device_relationships: Known relationships between devices.
    """

    session_id: str
    previous_reports: List[str] = field(default_factory=list)
    learned_patterns: Dict[str, Any] = field(default_factory=dict)
    device_relationships: Dict[str, List[str]] = field(default_factory=dict)

    def __str__(self) -> str:
        """Return a JSON representation of the workflow session."""
        return json.dumps(asdict(self), indent=2, default=str)


class InvestigationStatus(Enum):
    """Lifecycle state for a single device investigation.

    Values:
    - PENDING: Not yet started.
    - IN_PROGRESS: Currently being executed.
    - COMPLETED: Finished successfully.
    - FAILED: Exhausted retries without success.
    - SKIPPED: Not executed due to dependencies or plan changes.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

    def __str__(self) -> str:
        """Return the string value of the enum."""
        return self.value


class InvestigationPriority(Enum):
    """Priority level for investigation execution."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    def __str__(self) -> str:
        """Return the string value of the enum."""
        return self.value


@dataclass
class Investigation:
    """Encapsulates all work related to a specific device investigation.

    Attributes:
        device_name: Target device identifier extracted by input validator.
        device_profile: Device type/model information for context-aware planning.
        objective: Specific objective for this device investigation.
        working_plan_steps: Ordered execution steps tailored to this device.
        execution_results: Results from executing plan steps on this device.
        status: Current state of this investigation.
        priority: Execution priority level.
        dependencies: Other investigation device names this depends on.
        retry_count: Number of retries attempted for this specific investigation.
        report: Final investigation summary and findings.
        error_details: Error information if investigation failed.
    """

    device_name: str
    device_profile: str = ""
    role: str = ""
    objective: Optional[str] = None
    working_plan_steps: str = ""
    execution_results: List["StepExecutionResult"] = field(
        default_factory=list
    )

    status: InvestigationStatus = InvestigationStatus.PENDING
    priority: InvestigationPriority = InvestigationPriority.MEDIUM
    dependencies: List[str] = field(default_factory=list)

    report: Optional[str] = None
    error_details: Optional[str] = None

    def __str__(self) -> str:
        """Return a JSON representation of the investigation."""
        return json.dumps(asdict(self), indent=2, default=str)


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


@dataclass
class ExecutedToolCall:
    """Details of a single tool invocation made by the executor LLM.

    Attributes:
        function: Name of the tool invoked (e.g., "get_routing_info").
        params: Parameters passed to the tool.
        result: Structured result returned by the tool, if successful.
        error: Error message if the tool invocation failed.
    """

    function: str
    params: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def __str__(self) -> str:
        """Return a JSON representation of the tool call."""
        return json.dumps(asdict(self), indent=2, default=str)
