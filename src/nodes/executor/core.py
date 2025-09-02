"""
Core functionality for the Network Executor Node.

This module contains the main entry point for the executor workflow that handles
network operations for multiple device investigations concurrently.
"""

import asyncio
from dataclasses import replace

from schemas import GraphState
from src.logging import get_logger, log_node_execution

from .logging import log_incoming_state
from .execution import execute_investigations_concurrently
from .state import (
    update_state_with_investigations,
    update_state_with_global_error,
)

logger = get_logger(__name__)


@log_node_execution("Network Executor")
def llm_network_executor(state: GraphState) -> GraphState:
    """
    Execute network operations for multiple device investigations concurrently.

    This function orchestrates the complete investigation workflow by:
    1. Identifying pending investigations ready for execution
    2. Building appropriate prompts for each device investigation
    3. Executing commands concurrently via MCP agent
    4. Processing and structuring the responses
    5. Updating the workflow state with execution results

    Args:
        state: The current GraphState from the workflow

    Returns:
        Updated GraphState with execution results for all investigations
    """

    log_incoming_state(state)

    try:
        ready_investigations = state.get_ready_investigations()

        if not ready_investigations:
            logger.info("🔍 No investigations ready for execution")
            return state

        logger.info(
            "🚀 Starting execution for %s investigations",
            len(ready_investigations),
        )

        updated_investigations = asyncio.run(
            execute_investigations_concurrently(ready_investigations, state)
        )

        return update_state_with_investigations(state, updated_investigations)

    except Exception as e:
        logger.error("❌ Executor failed: %s", e)
        return update_state_with_global_error(state, e)
