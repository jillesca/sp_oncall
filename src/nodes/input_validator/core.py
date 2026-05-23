"""
Core functionality for the Input Validator Node.

This module contains the main entry point for the input validation workflow that
extracts device information and creates Investigation objects.
"""

import json
from dataclasses import replace
from typing import Optional

from schemas.state import GraphState
from src.logging import get_logger, log_node_execution
from nodes.common import load_fast_model

from .extraction import (
    execute_investigation_planning,
    extract_mcp_response_content,
)
from .processing import (
    process_investigation_planning_response,
    create_investigations_from_response,
)

logger = get_logger(__name__)


@log_node_execution("Input Validator")
def input_validator_node(state: GraphState) -> GraphState:
    """
    Input Validator node for multi-device investigation setup.

    This function orchestrates the multi-device investigation workflow by:
    1. Setting up the LLM model for extraction
    2. Extracting device names/information via MCP agent
    3. Processing the response to identify target devices
    4. Creating Investigation objects for each device
    5. Building the final state with investigations list and event_type

    Args:
        state: The current GraphState from the workflow

    Returns:
        Updated GraphState with investigations list and event_type populated,
        or error state
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
            return replace(state, investigations=[], event_type=event_type)

        investigations = create_investigations_from_response(
            investigation_list
        )
        _log_successful_investigation_planning(investigation_list)

        return replace(
            state, investigations=investigations, event_type=event_type
        )

    except Exception as e:
        logger.error("❌ Investigation planning failed with error: %s", e)
        return _build_failed_state(state)


def _extract_event_type(trigger_context: str) -> Optional[str]:
    """Extract event_type from a JSON alert trigger context, if present.

    Returns None for plain-text manual queries or malformed JSON.
    """
    try:
        data = json.loads(trigger_context)
        return data.get("event_type")
    except (json.JSONDecodeError, AttributeError):
        return None


def _log_successful_investigation_planning(devices) -> None:
    """Log successful investigation planning details."""
    logger.info(
        "✅ Investigation planning successful: %d devices created",
        len(devices),
    )
    for investigation in devices:
        logger.info(
            "  📋 %s (role: %s, profile: %s)",
            investigation.device_name,
            investigation.role,
            investigation.device_profile,
        )


def _build_failed_state(state: GraphState) -> GraphState:
    """Build a failed state when investigation planning fails."""
    logger.warning("🚨 Building failed state - no investigations created")
    return replace(state, investigations=[])
