"""
State management for executor investigations.

This module handles updating the GraphState with investigation results
and managing error conditions.
"""

from typing import List
from dataclasses import replace

from schemas import GraphState, Investigation, InvestigationStatus
from src.logging import get_logger

logger = get_logger(__name__)


def update_state_with_investigations(
    state: GraphState, updated_investigations: List[Investigation]
) -> GraphState:
    """
    Update the GraphState with completed investigations.

    Args:
        state: Current GraphState
        updated_investigations: List of updated investigations

    Returns:
        Updated GraphState
    """
    # Create a mapping of device names to updated investigations
    investigation_map = {
        inv.device_name: inv for inv in updated_investigations
    }

    updated_investigation_list = []
    for investigation in state.investigations:
        if investigation.device_name in investigation_map:
            updated_investigation_list.append(
                investigation_map[investigation.device_name]
            )
        else:
            # Keep the original investigation
            updated_investigation_list.append(investigation)

    logger.info(
        "📊 Updated %s investigations in state", len(updated_investigations)
    )

    return replace(state, investigations=updated_investigation_list)


def update_state_with_global_error(
    state: GraphState, error: Exception
) -> GraphState:
    """
    Update state with a global error that affects the entire workflow.

    Args:
        state: Current GraphState
        error: Exception that occurred during execution

    Returns:
        Updated GraphState with error information
    """
    logger.error("❌ Global execution error: %s", error)

    # Mark all ready investigations as failed
    updated_investigations = []
    for investigation in state.investigations:
        if investigation.status == InvestigationStatus.PENDING:
            failed_investigation = replace(
                investigation,
                status=InvestigationStatus.FAILED,
                error_details=f"Global execution error: {error}",
            )
            updated_investigations.append(failed_investigation)
        else:
            updated_investigations.append(investigation)

    return replace(state, investigations=updated_investigations)
