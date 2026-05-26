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


def _replace_list(_existing: list, new: list) -> list:
    """Replace-wins reducer: always take the incoming value.

    Prevents accumulation across graph runs. Nodes that carry state forward
    via replace(state, ...) pass the existing list as the new value, so the
    result is unchanged. The reporter clears these fields by returning a fresh
    GraphState with the default empty list.
    """
    return new


@dataclass
class GraphState:
    """Workflow state for the sp_oncall agent.

    Attributes:
        messages: Conversation history using LangChain message format.
        primary_investigations: One Investigation covering all primary devices
                                (alert target or explicitly requested). Typically
                                a single-element list; empty when none found.
        context_investigations: One Investigation covering all context (neighbor)
                                devices. Typically a single-element list.
        event_type: Alert event type extracted from the trigger context (e.g.
                    "interface_state", "bgp_session_state"). None for manual
                    queries.
        root_cause: Root cause analysis produced by the rca_assessor_node after
                    all investigations complete.
        context_phase_report: Single combined report produced by the context
                              executor covering all neighbor devices. Set by
                              collect_device_result in the context subgraph.
        context_device_names: Names of all devices covered by the context phase.
                              Used by downstream nodes (reporter, RCA) to build
                              headers without needing the full Investigation objects.
        completed_primary_investigations: Completed primary Investigation from
                                          the primary subgraph.
    """

    messages: Annotated[List[AnyMessage], add_messages] = field(
        default_factory=list
    )
    primary_investigations: List[Investigation] = field(default_factory=list)
    context_investigations: List[Investigation] = field(default_factory=list)
    event_type: Optional[str] = None
    root_cause: Optional[str] = None
    context_phase_report: str = ""
    context_device_names: List[str] = field(default_factory=list)
    completed_primary_investigations: Annotated[
        List[Investigation], _replace_list
    ] = field(default_factory=list)

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

    def __str__(self) -> str:
        """Return a JSON representation of the graph state."""
        return json.dumps(asdict(self), indent=2, default=str)


class InvestigationStatus(Enum):
    """Lifecycle state for a phase investigation.

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
    """Encapsulates one investigation attempt for all devices in a phase.

    Each Investigation covers every device assigned to the phase (context or
    primary). The planner produces a per-device plan stored in device_plans;
    the executor runs a single agent call across all devices and stores one
    combined report.

    Attributes:
        device_contexts: Maps device_name to its pre-formatted context string.
                         Assembled by the input validator from fresh MCP data,
                         stored dynamic facts, and investigation history.
                         Contains device facts, capabilities, and history for
                         that device only.
        device_plans: Maps device_name to its formatted investigation plan.
                      Populated by the planner node. Each value is plain text
                      containing the objective and ordered steps for that device.
                      Empty until the planner runs.
        execution_results: Results from all tool calls made by the executor agent.
        status: Current lifecycle state of this investigation.
        report: Single combined report produced by the executor covering all
                devices in this investigation. None until execution completes.
        error_details: Error information when the investigation failed.
    """

    device_contexts: Dict[str, str]
    device_plans: Dict[str, str] = field(default_factory=dict)
    execution_results: List["ExecutedToolCall"] = field(default_factory=list)
    status: InvestigationStatus = InvestigationStatus.PENDING
    report: Optional[str] = None
    error_details: Optional[str] = None

    def device_names(self) -> List[str]:
        """Return the ordered list of device names in this investigation."""
        return list(self.device_contexts.keys())

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
