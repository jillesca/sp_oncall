"""
Core execution logic for network investigations.

This module handles the execution of a single investigation via the MCP agent.
Concurrent execution across multiple devices is orchestrated by device_subgraph.py.
"""

from dataclasses import replace
from langchain_core.messages import HumanMessage

from schemas import Investigation, InvestigationStatus
from mcp_client import mcp_node
from src.util.prompt_loader import load_prompt
from src.logging import get_logger

from .context import build_investigation_context
from .processing import extract_response_content
from .logging import log_processed_data

logger = get_logger(__name__)


async def execute_single_investigation(
    investigation: Investigation, trigger_context: str
) -> Investigation:
    """
    Execute a single investigation using the MCP agent.

    Args:
        investigation: Investigation to execute
        trigger_context: Original trigger content for building the prompt

    Returns:
        Updated Investigation with execution results
    """
    logger.info(
        "🔍 Executing investigation for device: %s", investigation.device_name
    )

    try:
        context = build_investigation_context(investigation, trigger_context)
        message = HumanMessage(content=context)

        logger.debug(
            "📤 Sending to MCP agent for device %s", investigation.device_name
        )

        mcp_response = await mcp_node(
            message=message,
            system_prompt=load_prompt("network_executor"),
        )

        logger.debug(
            "📨 MCP agent response received for %s", investigation.device_name
        )

        llm_analysis, executed_tool_calls = extract_response_content(
            mcp_response
        )

        log_processed_data(llm_analysis, executed_tool_calls)

        updated_investigation = replace(
            investigation,
            status=InvestigationStatus.COMPLETED,
            execution_results=investigation.execution_results
            + executed_tool_calls,
            report=llm_analysis,
        )

        logger.info(
            "✅ Investigation completed for device: %s",
            investigation.device_name,
        )
        return updated_investigation

    except Exception as e:
        logger.error(
            "❌ Investigation failed for device %s: %s",
            investigation.device_name,
            e,
        )
        return replace(
            investigation,
            status=InvestigationStatus.FAILED,
            error_details=str(e),
        )
