"""
Core functionality for the Input Validator Node.

This module contains the main entry point for the input validation workflow that
extracts device information and creates Investigation objects.
"""

from dataclasses import replace

from schemas.state import GraphState
from src.logging import get_logger, log_node_execution
from nodes.common import load_model

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
    5. Building the final state with investigations list

    Args:
        state: The current GraphState from the workflow (should contain 'user_query')

    Returns:
        Updated GraphState with investigations list populated, or error state
    """

    try:
        logger.info("🔍 Starting multi-device investigation setup")
        model = load_model()
        mcp_response = execute_investigation_planning(state)
        response_content = extract_mcp_response_content(mcp_response)
        investigation_list = process_investigation_planning_response(
            response_content, model=model
        )

        # Happy path: Create Investigation objects and update state
        if not investigation_list or len(investigation_list) == 0:
            logger.warning(
                "⚠️ No devices found in investigation planning response"
            )
            return replace(state, investigations=[])

        investigations = create_investigations_from_response(
            investigation_list
        )
        _log_successful_investigation_planning(investigation_list)

        return replace(state, investigations=investigations)

    except Exception as e:
        logger.error("❌ Investigation planning failed with error: %s", e)
        return _build_failed_state(state)


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
    """
    Build a failed state when investigation planning fails.

    Args:
        state: Original state to preserve user_query and other data

    Returns:
        Updated GraphState with empty investigations list
    """
    logger.warning("🚨 Building failed state - no investigations created")
    return replace(state, investigations=[])
