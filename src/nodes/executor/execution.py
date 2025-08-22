"""
Core execution logic for network investigations.

This module handles the concurrent execution of multiple investigations
and processing of MCP agent responses.
"""

import asyncio
from typing import List
from dataclasses import replace
from langchain_core.messages import HumanMessage

from schemas import GraphState, Investigation, InvestigationStatus
from mcp_client import mcp_node
from prompts.network_executor import NETWORK_EXECUTOR_PROMPT
from src.logging import get_logger

from .context import build_investigation_context
from .processing import extract_response_content
from .logging import log_processed_data

logger = get_logger(__name__)


async def execute_investigations_concurrently(
    investigations: List[Investigation], state: GraphState
) -> List[Investigation]:
    """
    Execute multiple investigations concurrently and return updated investigations.

    Args:
        investigations: List of investigations ready for execution
        state: Current GraphState for workflow context

    Returns:
        List of updated Investigation objects with execution results
    """
    logger.info(
        "🚀 Starting concurrent execution for %s investigations",
        len(investigations),
    )

    # Create tasks for concurrent execution
    tasks = []
    for investigation in investigations:
        task = execute_single_investigation(investigation, state)
        tasks.append(task)

    # Execute all investigations concurrently
    completed_investigations = await asyncio.gather(
        *tasks, return_exceptions=True
    )

    # Process results and handle any exceptions
    updated_investigations = []
    for i, result in enumerate(completed_investigations):
        if isinstance(result, Exception):
            logger.error(
                "❌ Investigation failed for %s: %s",
                investigations[i].device_name,
                result,
            )
            # Create a failed investigation
            failed_investigation = replace(
                investigations[i],
                status=InvestigationStatus.FAILED,
                error_details=str(result),
            )
            updated_investigations.append(failed_investigation)
        else:
            updated_investigations.append(result)

    logger.info("✅ Completed %s investigations", len(updated_investigations))
    return updated_investigations


async def execute_single_investigation(
    investigation: Investigation, state: GraphState
) -> Investigation:
    """
    Execute a single investigation using the MCP agent.

    Args:
        investigation: Investigation to execute
        state: Current GraphState for workflow context

    Returns:
        Updated Investigation with execution results
    """
    logger.info(
        "🔍 Executing investigation for device: %s", investigation.device_name
    )

    try:
        context = build_investigation_context(investigation, state)
        message = HumanMessage(content=context)

        logger.debug(
            "📤 Sending to MCP agent for device %s", investigation.device_name
        )

        mcp_response = await mcp_node(
            message=message,
            system_prompt=NETWORK_EXECUTOR_PROMPT,
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
            report=llm_analysis,  # Store the investigation report
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
