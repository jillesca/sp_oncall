"""
Core functionality for the Input Validator Node.

This module contains the main entry point for the input validation workflow.
It orchestrates device discovery via MCP, hydrates each Investigation with
store context (dynamic facts + history), and creates the final Investigation
objects ready for the executor.

Devices marked is_primary by the discovery agent become primary_investigations.
All other discovered devices become context_investigations (neighbor health checks).
"""

import json
from dataclasses import replace
from typing import Optional, List, Tuple

from langgraph.config import get_store

from schemas.state import GraphState, Investigation
from schemas.device_capability_profile import format_capability_profile_for_context
from src.logging import get_logger, log_node_execution
from src.util.device_store import (
    get_device_profile,
    get_device_history,
    format_dynamic_facts_for_context,
    format_history_for_context,
)
from nodes.common import load_fast_model

from .extraction import (
    execute_investigation_planning,
    extract_mcp_response_content,
)
from .processing import (
    process_investigation_planning_response,
    InvestigationPlanningResponse,
    DiscoveredDevice,
)

logger = get_logger(__name__)


@log_node_execution("Input Validator")
def input_validator_node(state: GraphState) -> GraphState:
    """
    Input Validator node for multi-device investigation setup.

    Orchestrates the multi-device investigation workflow by:
    1. Calling MCP for fresh topology discovery (always runs)
    2. For each discovered device, loading stored dynamic facts and history
    3. Splitting devices into primary investigations (alert targets) and
       context investigations (neighbor health checks)
    4. Returning the updated GraphState with both investigation lists and event_type

    Args:
        state: The current GraphState from the workflow

    Returns:
        Updated GraphState with primary_investigations, context_investigations,
        and event_type populated, or error state
    """
    try:
        logger.info("🔍 Starting multi-device investigation setup")
        fast_model = load_fast_model()
        mcp_response = execute_investigation_planning(state)
        response_content = extract_mcp_response_content(mcp_response)
        investigation_list = process_investigation_planning_response(
            response_content, model=fast_model
        )

        event_type = _extract_event_type(state.trigger_context)
        if event_type:
            logger.info("🔔 Alert event_type detected: %s", event_type)

        if not investigation_list or len(investigation_list) == 0:
            logger.warning(
                "⚠️ No devices found in investigation planning response"
            )
            return replace(
                state,
                primary_investigations=[],
                context_investigations=[],
                event_type=event_type,
            )

        store = get_store()
        primary_investigations, context_investigations = _hydrate_and_split(
            investigation_list, store
        )
        _log_successful_investigation_planning(
            primary_investigations, context_investigations
        )

        return replace(
            state,
            primary_investigations=primary_investigations,
            context_investigations=context_investigations,
            event_type=event_type,
        )

    except Exception as e:
        logger.error("❌ Investigation planning failed with error: %s", e)
        return _build_failed_state(state)


def _hydrate_and_split(
    investigation_list: InvestigationPlanningResponse, store
) -> Tuple[List[Investigation], List[Investigation]]:
    """Hydrate all discovered devices and split into primary and context lists.

    Primary investigations are for devices the alert or user request explicitly
    targets. Context investigations are neighbor devices checked for health.
    """
    primary = []
    context = []

    for device in investigation_list:
        investigation = _hydrate_single_investigation(device, store)
        if device.is_primary:
            primary.append(investigation)
        else:
            context.append(investigation)

    return primary, context


def _hydrate_single_investigation(
    device: DiscoveredDevice, store
) -> Investigation:
    """Build a single Investigation hydrated from fresh MCP data and store context."""
    profile = get_device_profile(store, device.device_name)
    history = get_device_history(store, device.device_name, limit=3)
    device_context = _build_device_context(device, profile, history)

    logger.debug(
        "  ✅ Hydrated investigation for %s (role=%s, neighbors=%s, has_history=%s, is_primary=%s, has_capability_profile=%s)",
        device.device_name,
        device.role or "unknown",
        device.neighbors,
        bool(history),
        device.is_primary,
        device.capability_profile is not None,
    )

    return Investigation(
        device_name=device.device_name,
        device_context=device_context,
        role=device.role,
        neighbors=device.neighbors,
        capability_profile=device.capability_profile,
    )


def _build_device_context(
    device: DiscoveredDevice, profile: dict, history: list
) -> str:
    """Assemble device_context from fresh MCP data and stored historical context.

    Static topology (type, role, neighbors) and capability profile always come
    from the current MCP response. The store contributes only dynamic facts and
    investigation history to avoid stale topology data.
    """
    sections = [_format_mcp_device_section(device)]

    capability_context = format_capability_profile_for_context(device.capability_profile)
    if capability_context:
        sections.append(capability_context)

    dynamic_context = format_dynamic_facts_for_context(profile)
    if dynamic_context:
        sections.append(dynamic_context)

    history_context = format_history_for_context(history)
    if history_context:
        sections.append(history_context)

    return "\n\n".join(sections)


def _format_mcp_device_section(device: DiscoveredDevice) -> str:
    """Format the fresh MCP-provided device facts as a context section."""
    lines = ["Device Facts:"]
    lines.append(f"  Type/Model: {device.type_model or 'Unknown'}")
    lines.append(f"  Role: {device.role or 'Unknown'}")
    if device.neighbors:
        lines.append(f"  Neighbors: {', '.join(device.neighbors)}")
    return "\n".join(lines)


def _extract_event_type(trigger_context: str) -> Optional[str]:
    """Extract event_type from a JSON alert trigger context, if present.

    Returns None for plain-text manual queries or malformed JSON.
    """
    try:
        data = json.loads(trigger_context)
        return data.get("event_type")
    except (json.JSONDecodeError, AttributeError):
        return None


def _log_successful_investigation_planning(
    primary_investigations: List[Investigation],
    context_investigations: List[Investigation],
) -> None:
    """Log successful investigation planning details."""
    logger.info(
        "✅ Investigation planning successful: %d primary, %d context devices",
        len(primary_investigations),
        len(context_investigations),
    )
    for inv in primary_investigations:
        logger.info(
            "  🎯 PRIMARY %s | role=%s | neighbors=%s",
            inv.device_name,
            inv.role or "unknown",
            inv.neighbors,
        )
    for inv in context_investigations:
        logger.info(
            "  📋 CONTEXT %s | role=%s | neighbors=%s",
            inv.device_name,
            inv.role or "unknown",
            inv.neighbors,
        )


def _build_failed_state(state: GraphState) -> GraphState:
    """Build a failed state when investigation planning fails."""
    logger.warning("🚨 Building failed state - no investigations created")
    return replace(state, primary_investigations=[], context_investigations=[])
