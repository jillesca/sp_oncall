"""
State management for executor investigations.

This module handles updating the GraphState with investigation results
and managing error conditions for both primary and context executor nodes.
"""

from typing import List
from dataclasses import replace

from schemas import GraphState, Investigation, InvestigationStatus
from src.logging import get_logger

logger = get_logger(__name__)


def update_context_investigations(
    state: GraphState, completed: List[Investigation]
) -> GraphState:
    """Replace context_investigations with completed results."""
    logger.info("📊 Updated %s context investigations in state", len(completed))
    return replace(state, context_investigations=_merge(state.context_investigations, completed))


def update_primary_investigations(
    state: GraphState, completed: List[Investigation]
) -> GraphState:
    """Replace primary_investigations with completed results."""
    logger.info("📊 Updated %s primary investigations in state", len(completed))
    return replace(state, primary_investigations=_merge(state.primary_investigations, completed))


def mark_all_failed(
    investigations: List[Investigation], error: Exception
) -> List[Investigation]:
    """Mark all pending investigations as failed due to a global executor error."""
    logger.error("❌ Global execution error: %s", error)
    return [
        replace(
            inv,
            status=InvestigationStatus.FAILED,
            error_details=f"Global execution error: {error}",
        )
        if inv.status == InvestigationStatus.PENDING
        else inv
        for inv in investigations
    ]


def _merge(
    original: List[Investigation], updated: List[Investigation]
) -> List[Investigation]:
    """Overlay updated investigations onto the original list by device name."""
    updated_map = {inv.device_name: inv for inv in updated}
    return [
        updated_map.get(inv.device_name, inv)
        for inv in original
    ]
