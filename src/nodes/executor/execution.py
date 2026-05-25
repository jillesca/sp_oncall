"""
Phase execution for network investigations.

One MCP agent call handles all devices within an investigation phase,
receiving combined device context and producing a single set of findings.
"""

from dataclasses import replace
from typing import List

from langchain_core.messages import HumanMessage

from schemas import Investigation, InvestigationStatus
from mcp_client import mcp_node
from src.util.prompt_loader import load_prompt
from src.logging import get_logger

from .context import build_phase_context
from .processing import extract_response_content
from .logging import log_processed_data

logger = get_logger(__name__)


async def execute_phase_investigations(
    investigations: List[Investigation],
    trigger_context: str,
    executor_prompt: str,
) -> List[Investigation]:
    """Execute a phase's investigations using a single MCP agent call.

    Builds combined context for all devices in the phase and runs one agent.
    The agent investigates all N devices and produces combined findings
    that are attributed to each investigation in the phase.

    Args:
        investigations: Devices to investigate in this phase.
        trigger_context: Original trigger content for prompt assembly.
        executor_prompt: Name of the prompt file to use as the system prompt.

    Returns:
        Updated investigations marked completed or failed.
    """
    device_names = [inv.device_name for inv in investigations]
    logger.info(
        "🔍 Executing phase for device(s): %s (prompt=%s)",
        device_names,
        executor_prompt,
    )

    try:
        context = build_phase_context(investigations, trigger_context)
        message = HumanMessage(content=context)

        mcp_response = await mcp_node(
            message=message,
            system_prompt=load_prompt(executor_prompt),
        )

        llm_analysis, executed_tool_calls = extract_response_content(mcp_response)
        log_processed_data(llm_analysis, executed_tool_calls)

        logger.info("✅ Phase investigation completed for: %s", device_names)

        return [
            replace(
                inv,
                status=InvestigationStatus.COMPLETED,
                execution_results=inv.execution_results + executed_tool_calls,
                report=llm_analysis,
            )
            for inv in investigations
        ]

    except Exception as e:
        logger.error("❌ Phase investigation failed for %s: %s", device_names, e)
        return [
            replace(inv, status=InvestigationStatus.FAILED, error_details=str(e))
            for inv in investigations
        ]
