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

from .device_capability_profile import DeviceCapabilityProfile


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
        primary_investigations: Pending investigations for devices named in the
                                trigger (alert target or explicitly requested).
        context_investigations: Pending investigations for neighbor devices
                                discovered by the input validator.
        event_type: Alert event type extracted from the trigger context (e.g.
                    "interface_state", "bgp_session_state"). None for manual
                    queries.
        root_cause: Root cause analysis produced by the rca_assessor_node after
                    all investigations complete.
        context_phase_report: Single combined report produced by the context
                              executor covering all neighbor devices at once.
                              Set by collect_device_result in the context subgraph.
                              Used by downstream nodes instead of iterating
                              completed_context_investigations for report content.
        completed_context_investigations: Completed context Investigation objects
                                          from the context subgraph. Carries device
                                          metadata (name, role, capability_profile,
                                          status) but not used for report content
                                          — use context_phase_report instead.
        completed_primary_investigations: Completed primary device results produced
                                          by the primary_investigation subgraph.
    """

    messages: Annotated[List[AnyMessage], add_messages] = field(
        default_factory=list
    )
    primary_investigations: List[Investigation] = field(default_factory=list)
    context_investigations: List[Investigation] = field(default_factory=list)
    event_type: Optional[str] = None
    root_cause: Optional[str] = None
    context_phase_report: str = ""
    completed_context_investigations: Annotated[
        List[Investigation], _replace_list
    ] = field(default_factory=list)
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
        device_context: Pre-formatted prompt-ready string assembled by the input validator
                        from fresh MCP data plus stored dynamic facts and investigation history.
                        Contains only facts about this device — never neighbor reports.
        neighbor_context: Pre-formatted markdown of completed neighbor health check reports.
                          Populated by enrich_primary_investigations before the primary phase.
                          Empty for context investigations.
        role: Device role in the topology (PE, P, PCE, vRR).
        neighbors: Directly connected devices discovered during input validation.
        capability_profile: Protocol and feature flags from the get_device_profile_api MCP
                            call. None when the MCP call returned no data. Carried through
                            the graph so the reporter can persist it to static_facts.
        objective: Specific objective for this device investigation.
        working_plan_steps: Ordered execution steps tailored to this device.
        execution_results: Results from executing plan steps on this device.
        status: Current lifecycle state of this investigation.
        report: Final investigation summary and findings.
        error_details: Error information if investigation failed.
    """

    device_name: str
    device_context: str = ""
    neighbor_context: str = ""
    role: str = ""
    neighbors: List[str] = field(default_factory=list)
    capability_profile: Optional[DeviceCapabilityProfile] = None
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
