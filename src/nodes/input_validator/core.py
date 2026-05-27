"""
Core functionality for the Input Validator Node.

This module contains the main entry point for the input validation workflow.
It orchestrates device discovery via MCP, hydrates each device with store
context (dynamic facts + history), and builds one Investigation per phase:
- One Investigation for all primary devices (alert target or user request)
- One Investigation for all context devices (neighbor health checks)
"""

import json
from dataclasses import replace
from typing import Optional, Tuple

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
from src.util.prompt_logger import start_run

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
    3. Grouping devices into two phase Investigations:
       - primary_investigations: one Investigation covering all primary devices
       - context_investigations: one Investigation covering all context devices
    4. Returning the updated GraphState with both investigation lists and event_type

    Args:
        state: The current GraphState from the workflow

    Returns:
        Updated GraphState with primary_investigations, context_investigations,
        and event_type populated, or error state
    """
    try:
        start_run()
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
        primary_investigation, context_investigation = _build_phase_investigations(
            investigation_list, store
        )
        _log_successful_investigation_planning(
            primary_investigation, context_investigation
        )

        return replace(
            state,
            primary_investigations=(
                [primary_investigation] if primary_investigation else []
            ),
            context_investigations=(
                [context_investigation] if context_investigation else []
            ),
            event_type=event_type,
        )

    except Exception as e:
        logger.error("❌ Investigation planning failed with error: %s", e)
        return _build_failed_state(state)


def _build_phase_investigations(
    investigation_list: InvestigationPlanningResponse, store
) -> Tuple[Optional[Investigation], Optional[Investigation]]:
    """Build one Investigation per phase from all discovered devices.

    Each device's context is assembled from fresh MCP data and stored history,
    then grouped into primary or context device_contexts dicts.
    """
    primary_contexts: dict = {}
    context_contexts: dict = {}

    for device in investigation_list:
        profile = get_device_profile(store, device.device_name)
        history = get_device_history(store, device.device_name, limit=3)
        device_context = _build_device_context(
            device, profile, history, include_dynamic_facts=device.is_primary
        )

        logger.debug(
            "  ✅ Hydrated context for %s (role=%s, is_primary=%s)",
            device.device_name,
            device.role or "unknown",
            device.is_primary,
        )

        if device.is_primary:
            primary_contexts[device.device_name] = device_context
        else:
            context_contexts[device.device_name] = device_context

    primary = Investigation(device_contexts=primary_contexts) if primary_contexts else None
    context = Investigation(device_contexts=context_contexts) if context_contexts else None

    return primary, context


def _build_device_context(
    device: DiscoveredDevice,
    profile: dict,
    history: list,
    include_dynamic_facts: bool = True,
) -> str:
    """Assemble device_context from fresh MCP data and stored historical context.

    Static topology (type, role, neighbors) and capability profile always come
    from the current MCP response. The store contributes only dynamic facts and
    investigation history to avoid stale topology data.

    Dynamic facts (DEVICE_PROFILE) are excluded for context devices because
    they carry the last alert text — which references the primary device — and
    confuse the context executor into thinking it is investigating that device.
    """
    sections = [_format_mcp_device_section(device)]

    capability_context = format_capability_profile_for_context(device.capability_profile)
    if capability_context:
        sections.append(capability_context)

    if include_dynamic_facts:
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
    primary_investigation: Optional[Investigation],
    context_investigation: Optional[Investigation],
) -> None:
    """Log successful investigation planning details."""
    primary_count = len(primary_investigation.device_contexts) if primary_investigation else 0
    context_count = len(context_investigation.device_contexts) if context_investigation else 0

    logger.info(
        "✅ Investigation planning successful: %d primary, %d context devices",
        primary_count,
        context_count,
    )
    if primary_investigation:
        for device_name in primary_investigation.device_contexts:
            logger.info("  🎯 PRIMARY %s", device_name)
    if context_investigation:
        for device_name in context_investigation.device_contexts:
            logger.info("  📋 CONTEXT %s", device_name)


def _build_failed_state(state: GraphState) -> GraphState:
    """Build a failed state when investigation planning fails."""
    logger.warning("🚨 Building failed state - no investigations created")
    return replace(state, primary_investigations=[], context_investigations=[])
