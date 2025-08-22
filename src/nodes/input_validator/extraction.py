"""
Device extraction functionality for input validation.

This module handles extracting device information via MCP agent
and processing MCP responses for device identification.
"""

import asyncio
from typing import Any

from langchain_core.messages import HumanMessage, AIMessage
from prompts.investigation_planning import INVESTIGATION_PLANNING_PROMPT
from mcp_client import mcp_node
from src.logging import get_logger

logger = get_logger(__name__)


def execute_investigation_planning(
    user_query: str, response_format: Any = None
) -> dict:
    """
    Execute investigation planning via MCP agent.

    Args:
        user_query: The user's query that needs investigation planning
        response_format: Optional response format specification

    Returns:
        MCP response containing investigation planning results
    """
    logger.debug(
        "🔗 Executing investigation planning via MCP agent. User query: %s",
        user_query,
    )

    message = HumanMessage(content=f"User query: {user_query}")

    return asyncio.run(
        mcp_node(
            message=message,
            system_prompt=INVESTIGATION_PLANNING_PROMPT,
            response_format=response_format,
        )
    )


def extract_mcp_response_content(mcp_response: Any) -> Any:
    """
    Extract content from MCP response for device name processing.

    The MCP response contains a 'messages' list with AIMessage and ToolMessage objects.
    We need to get the content from the last AIMessage which contains the final result.

    Args:
        mcp_response: Raw response from MCP agent containing messages list

    Returns:
        Extracted content string from the last AIMessage

    Raises:
        ValueError: If response format is invalid or no AIMessage found
    """
    logger.debug("📋 Extracting content from MCP response")
    logger.debug(
        "🔍 MCP response keys: %s",
        (
            list(mcp_response.keys())
            if isinstance(mcp_response, dict)
            else "Not a dict"
        ),
    )

    # Check if the response has the expected structure
    if not isinstance(mcp_response, dict) or "messages" not in mcp_response:
        logger.error("❌ Invalid MCP response: missing 'messages' key")
        raise ValueError("Invalid MCP response format: missing 'messages' key")

    messages = mcp_response["messages"]
    if not isinstance(messages, list) or len(messages) == 0:
        logger.error(
            "❌ Invalid MCP response: 'messages' is not a list or is empty"
        )
        raise ValueError(
            "Invalid MCP response format: 'messages' is not a list or is empty"
        )

    # Find the last AIMessage in the messages list
    last_ai_message = None
    for message in reversed(messages):
        if hasattr(message, "content") and hasattr(message, "__class__"):
            if isinstance(message, AIMessage):
                last_ai_message = message
                break

    if last_ai_message is None:
        logger.error("❌ No AIMessage found in MCP response messages")
        raise ValueError("No AIMessage found in MCP response messages")

    logger.debug("🎯 Content: %s", last_ai_message.content)

    return last_ai_message
