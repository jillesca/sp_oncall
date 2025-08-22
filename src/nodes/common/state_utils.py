"""
Common state management utilities for all nodes.

This module provides shared functionality for state management operations
that are used across different nodes to maintain consistency.
"""

from typing import List, Dict, Any
from dataclasses import replace

from schemas.state import GraphState, Investigation
from src.logging import get_logger

logger = get_logger(__name__)


def build_error_state(
    state: GraphState, error: Exception, error_message: str = None
) -> GraphState:
    """
    Build a GraphState for error scenarios.

    Args:
        state: Current GraphState
        error: Exception that occurred
        error_message: Optional custom error message

    Returns:
        Updated GraphState with error information
    """
    logger.error("❌ Building error state: %s", error)

    if error_message is None:
        error_message = f"Operation failed: {error}"

    # For now, return the state unchanged - specific nodes can override this behavior
    return state


def apply_updates_to_investigations(
    state: GraphState, updates: Dict[str, Dict[str, Any]]
) -> GraphState:
    """
    Apply updates to investigations by device name.

    Args:
        state: Current GraphState
        updates: Dictionary mapping device_name to update fields

    Returns:
        Updated GraphState with investigation updates applied
    """
    updated_investigations = []

    for investigation in state.investigations:
        if investigation.device_name in updates:
            update_fields = updates[investigation.device_name]
            updated_investigation = replace(investigation, **update_fields)
            updated_investigations.append(updated_investigation)
            logger.debug(
                "📝 Updated investigation for device: %s",
                investigation.device_name,
            )
        else:
            updated_investigations.append(investigation)

    return replace(state, investigations=updated_investigations)


def get_investigations_by_status(
    investigations: List[Investigation], status
) -> List[Investigation]:
    """
    Filter investigations by status.

    Args:
        investigations: List of investigations to filter
        status: Status to filter by

    Returns:
        List of investigations with the specified status
    """
    return [inv for inv in investigations if inv.status == status]


def create_investigation_mapping(
    investigations: List[Investigation],
) -> Dict[str, Investigation]:
    """
    Create a mapping of device name to investigation.

    Args:
        investigations: List of investigations

    Returns:
        Dictionary mapping device names to investigation objects
    """
    return {inv.device_name: inv for inv in investigations}
