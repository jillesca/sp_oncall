"""
Core functionality for the Objective Assessor Node.

This node is not part of the outer graph in Stage 1.1.
Stage 1.2 will integrate it into the per-device sub-graph operating on DeviceState.
"""

from schemas import GraphState
from src.logging import get_logger

logger = get_logger(__name__)


def objective_assessor_node(state: GraphState) -> GraphState:
    """
    Placeholder for objective assessor — wired into per-device sub-graph in Stage 1.2.
    """
    logger.debug("Assessor node called (stub — Stage 1.2 will implement per-device logic)")
    return state
