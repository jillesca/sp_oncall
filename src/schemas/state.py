"""
Define the state structures for the agent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Any, Optional, Annotated

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph.message import add_messages


@dataclass
class GraphState:
    """Workflow state for the sp_oncall agent.

    Attributes:
        messages: Conversation history using LangChain message format.
        investigations: Collection of device-specific investigations.
        event_type: Alert event type extracted from the trigger context (e.g.
                    "interface_state", "bgp_session_state"). None for manual
                    queries.
    """

    messages: Annotated[List[AnyMessage], add_messages] = field(
        default_factory=list
    )
    investigations: List[Investigation] = field(default_factory=list)
    event_type: Optional[str] = None

    @property
    def trigger_context(self) -> str:
        """Extract the most recent trigger content.

        Returns the content of the most recent human message, whether it
        originates from a user query, an alert from an observability system,
        or an upstream agent.
        Handles both string content and structured content (list of content blocks).
        """
        for message in reversed(self.messages):
            if isinstance(message, HumanMessage):
                content = message.content

                if isinstance(content, list):
                    text_parts = []
                    for block in content:
                        if (
                            isinstance(block, dict)
                            and block.get("type") == "text"
                        ):
                            text_parts.append(block.get("text", ""))
                        elif isinstance(block, str):
                            text_parts.append(block)
                    return " ".join(text_parts)

                elif isinstance(content, str):
                    return content

                else:
                    return str(content)

        return ""

    def get_pending_investigations(self) -> List["Investigation"]:
        """Return all investigations that have not yet been executed."""
        return [
            inv
            for inv in self.investigations
            if inv.status == InvestigationStatus.PENDING
        ]

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


class InvestigationStatus(Enum):
    """Lifecycle state for a single device investigation.

    Values:
    - PENDING: Not yet started.
    - IN_PROGRESS: Currently being executed.
    - COMPLETED: Finished successfully.
    - FAILED: Exhausted retries without success.
    - SKIPPED: Not executed due to plan changes.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

    def __str__(self) -> str:
        """Return the string value of the enum."""
        return self.value


@dataclass
class Investigation:
    """Encapsulates all work related to a specific device investigation.

    Attributes:
        device_name: Target device identifier extracted by input validator.
        device_profile: Device type/model information for context-aware planning.
        role: Device role in the topology (PE, P, PCE, vRR).
        neighbors: Directly connected devices discovered during input validation.
        objective: Specific objective for this device investigation.
        working_plan_steps: Ordered execution steps tailored to this device.
        execution_results: Results from executing plan steps on this device.
        status: Current lifecycle state of this investigation.
        report: Final investigation summary and findings.
        error_details: Error information if investigation failed.
    """

    device_name: str
    device_profile: str = ""
    role: str = ""
    neighbors: List[str] = field(default_factory=list)
    objective: Optional[str] = None
    working_plan_steps: str = ""
    execution_results: List["ExecutedToolCall"] = field(default_factory=list)
    status: InvestigationStatus = InvestigationStatus.PENDING
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
