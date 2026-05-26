"""
Phase execution for network investigations.

One MCP agent call handles all devices within an investigation phase,
receiving combined device context and producing a single set of findings.
"""

from dataclasses import replace

from langchain_core.messages import HumanMessage

from schemas import Investigation, InvestigationStatus
from mcp_client import mcp_node
from src.util.prompt_loader import load_prompt
from src.util.prompt_logger import log_prompt
from src.logging import get_logger

from .context import build_phase_context
from .processing import extract_response_content
from .logging import log_processed_data

logger = get_logger(__name__)


async def execute_phase_investigations(
    investigation: Investigation,
    trigger_context: str,
    executor_prompt: str,
    context_phase_report: str = "",
    attempt: int = 1,
) -> Investigation:
    """Execute a phase's investigation using a single MCP agent call.

    Builds combined context for all devices in the phase and runs one agent.
    The agent investigates all devices and produces one combined report
    attributed to this investigation.

    Args:
        investigation: Phase investigation covering all devices.
        trigger_context: Original trigger content for prompt assembly.
        executor_prompt: Name of the prompt file to use as the system prompt.
        context_phase_report: Neighbor health check findings (primary phase only).
        attempt: Retry attempt number (1-based), used for prompt log filenames.

    Returns:
        Updated investigation marked completed or failed.
    """
    device_names = investigation.device_names()
    logger.info(
        "🔍 Executing phase for device(s): %s (prompt=%s, attempt=%s)",
        device_names,
        executor_prompt,
        attempt,
    )

    try:
        context = build_phase_context(
            investigation, trigger_context, context_phase_report
        )
        system_prompt = load_prompt(executor_prompt)

        log_prompt(
            node_name=executor_prompt,
            system_prompt=system_prompt,
            human_message=context,
            attempt=attempt,
        )

        message = HumanMessage(content=context)
        mcp_response = await mcp_node(message=message, system_prompt=system_prompt)

        llm_analysis, executed_tool_calls = extract_response_content(mcp_response)
        log_processed_data(llm_analysis, executed_tool_calls)

        logger.info("✅ Phase investigation completed for: %s", device_names)

        return replace(
            investigation,
            status=InvestigationStatus.COMPLETED,
            execution_results=investigation.execution_results + executed_tool_calls,
            report=llm_analysis,
        )

    except Exception as e:
        logger.error("❌ Phase investigation failed for %s: %s", device_names, e)
        return replace(
            investigation, status=InvestigationStatus.FAILED, error_details=str(e)
        )
