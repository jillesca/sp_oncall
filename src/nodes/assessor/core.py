"""
Core functionality for the Objective Assessor Node.

This module contains the main entry point for the assessor workflow that evaluates
investigations and determines workflow completion status.
"""

from schemas import GraphState
from src.logging import get_logger, log_node_execution
from nodes.common import load_model
from prompts.objective_assessor import OBJECTIVE_ASSESSOR_PROMPT

from .context import build_assessment_context
from .assessment import execute_assessment
from .state import apply_assessment_to_workflow, handle_assessment_error

logger = get_logger(__name__)


@log_node_execution("Objective Assessor")
def objective_assessor_node(state: GraphState) -> GraphState:
    """
    Unified objective assessor node that evaluates all investigations and determines workflow completion.

    This function orchestrates the assessment workflow by:
    1. Building comprehensive context from all investigations
    2. Setting up the LLM model for assessment
    3. Generating assessment prompt and executing assessment
    4. Processing the assessment response
    5. Applying assessment decisions to update workflow state

    Args:
        state: The current workflow state containing user query, investigations, etc.

    Returns:
        Updated workflow state with the assessment results and next steps.
    """
    logger.info(
        "🔍 Assessing overall objective achievement for %d investigations",
        len(state.investigations),
    )

    try:
        assessment_context = build_assessment_context(state)
        model = load_model()
        ai_assessment = execute_assessment(
            model, assessment_context, OBJECTIVE_ASSESSOR_PROMPT
        )
        return apply_assessment_to_workflow(state, ai_assessment)

    except (ValueError, TypeError, AttributeError) as e:
        logger.error("❌ Assessment failed: %s", e)
        return handle_assessment_error(state, e)
    except Exception as e:  # Catch all other unexpected errors
        logger.error("❌ Unexpected assessment error: %s", e)
        return handle_assessment_error(state, e)
