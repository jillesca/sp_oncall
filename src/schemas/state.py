"""
Define the state structures for the agent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Any, Optional

from .assessment_schema import AssessmentOutput


@dataclass
class GraphState:
    """Enhanced workflow state supporting multi-device investigations.

    Attributes:
        user_query: Original user question or task description.
        investigations: Collection of device-specific investigations.
        historical_context: Historical context and learned patterns from previous investigations.

        # Global workflow control
        max_retries: Maximum retry attempts per investigation.
        current_retries: Global retry counter for the entire workflow.

        # Assessment results (composition with AssessmentOutput)
        assessment: Assessment results from the objective assessor node.
                   Contains is_objective_achieved, notes_for_final_report, and feedback_for_retry.

        # Final output
        final_report: Comprehensive report combining all investigations.
    """

    user_query: str
    investigations: List[Investigation] = field(default_factory=list)
    historical_context: List[HistoricalContext] = field(default_factory=list)

    # Global workflow control
    max_retries: int = 3
    current_retries: int = 0

    assessment: Optional[AssessmentOutput] = None

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
class HistoricalContext:
    """Represents historical context and learnings from a previous investigation session.

    This class stores valuable insights from past investigations that can be used
    to provide context to LLMs for improved decision-making in current investigations.

    Attributes:
        session_id: Unique identifier for the historical investigation session.
        previous_report: Investigation report from the historical session.
        learned_patterns: Patterns discovered from the historical investigation (markdown formatted).
        device_relationships: Known relationships between devices discovered historically (markdown formatted).
    """

    session_id: str
    previous_report: str = ""
    learned_patterns: str = ""
    device_relationships: str = ""

    def __str__(self) -> str:
        """Return a JSON representation of the historical context."""
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
    execution_results: List["ExecutedToolCall"] = field(default_factory=list)

    status: InvestigationStatus = InvestigationStatus.PENDING
    priority: InvestigationPriority = InvestigationPriority.MEDIUM
    dependencies: List[str] = field(default_factory=list)

    report: Optional[str] = None
    error_details: Optional[str] = None

    def __str__(self) -> str:
        """Return a JSON representation of the investigation."""
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
