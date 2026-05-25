"""
Root Cause Analysis Assessor Node.

Synthesizes all primary and context investigation reports into a single
definitive root cause determination. Runs after all executor nodes complete
and before the reporter formats the final output.
"""

from dataclasses import replace

from langchain_core.messages import SystemMessage, HumanMessage

from schemas import GraphState
from nodes.common import load_model
from src.util.prompt_loader import load_prompt
from src.util.prompt_logger import log_prompt
from src.logging import get_logger, log_node_execution

from .context import build_rca_context

logger = get_logger(__name__)


@log_node_execution("RCA Assessor")
def rca_assessor_node(state: GraphState) -> GraphState:
    """
    Synthesize all investigation reports into a root cause determination.

    Reads completed primary and context investigations, builds a unified
    analysis context, and invokes the LLM to produce a root_cause string
    that the reporter uses as the authoritative RCA finding.

    Args:
        state: The current GraphState with all completed investigations

    Returns:
        Updated GraphState with root_cause populated
    """
    logger.info(
        "🔬 Starting RCA synthesis: %s primary, %s context investigations",
        len(state.completed_primary_investigations),
        len(state.completed_context_investigations),
    )

    try:
        rca_context = build_rca_context(state)
        model = load_model()
        system_prompt = load_prompt("rca_assessor")

        log_prompt(
            node_name="rca_assessor",
            system_prompt=system_prompt,
            human_message=rca_context,
        )

        response = model.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=rca_context),
            ]
        )

        root_cause = response.content
        logger.info(
            "✅ RCA synthesis complete (%d characters)", len(root_cause)
        )

        return replace(state, root_cause=root_cause)

    except Exception as e:
        logger.error("❌ RCA assessment failed: %s", e)
        return replace(
            state,
            root_cause=f"Root cause analysis could not be completed. Error: {e}",
        )
