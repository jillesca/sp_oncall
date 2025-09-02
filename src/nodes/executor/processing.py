"""
Response processing for executor investigations.

This module handles processing MCP agent responses and converting
them into structured investigation results.
"""

from typing import List, Tuple
from langchain_core.messages import AIMessage, ToolMessage

from schemas import ExecutedToolCall
from src.logging import get_logger

logger = get_logger(__name__)


def extract_response_content(
    mcp_response: dict,
) -> Tuple[str, List[ExecutedToolCall]]:
    """
    Extract LLM analysis and tool execution results from MCP agent response.

    Args:
        mcp_response: Response from MCP agent containing messages

    Returns:
        Tuple of (llm_analysis_content, executed_tool_calls)

    Raises:
        ValueError: If no valid response content found
    """
    logger.debug(
        "📨 MCP response keys: %s",
        (
            list(mcp_response.keys())
            if isinstance(mcp_response, dict)
            else "Not a dict"
        ),
    )

    messages = mcp_response.get("messages", [])
    logger.debug("📨 MCP response contains %s messages", len(messages))

    if not messages:
        logger.error("❌ No messages found in MCP response")
        raise ValueError("No messages found in MCP response")

    # Extract the last AIMessage (contains LLM analysis)
    llm_analysis = extract_last_ai_message(messages)

    # Extract all ToolMessages (contains tool execution results)
    executed_tool_calls = extract_tool_messages(messages)

    logger.debug(
        "📨 Extracted %s tool calls and LLM analysis (%s chars)",
        len(executed_tool_calls),
        len(llm_analysis),
    )

    return llm_analysis, executed_tool_calls


def extract_last_ai_message(messages: List) -> str:
    """
    Extract content from the last AIMessage in the message list.

    Args:
        messages: List of LangChain messages

    Returns:
        Content string from the last AIMessage

    Raises:
        ValueError: If no AIMessage found
    """
    # Find all AIMessages and get the last one
    ai_messages = [msg for msg in messages if isinstance(msg, AIMessage)]

    if not ai_messages:
        logger.error("❌ No AIMessage found in messages")
        raise ValueError("No AIMessage found in messages")

    last_ai_message = ai_messages[-1]
    content = last_ai_message.content

    # Handle both string and list content types
    if isinstance(content, str):
        content_str = content
    elif isinstance(content, list):
        # Join list content into a single string
        content_str = " ".join(str(item) for item in content)
    else:
        content_str = str(content)

    logger.debug(
        "📨 Found %s AIMessages, using last one with %s characters",
        len(ai_messages),
        len(content_str),
    )
    logger.debug("📨 Last AI message preview: %s...", content_str[:500])

    return content_str


def extract_tool_messages(messages: List) -> List[ExecutedToolCall]:
    """
    Extract and convert ToolMessages to ExecutedToolCall objects.

    Args:
        messages: List of LangChain messages

    Returns:
        List of ExecutedToolCall objects
    """
    tool_messages = [msg for msg in messages if isinstance(msg, ToolMessage)]
    executed_calls = []

    logger.debug("📞 Found %s ToolMessages to process", len(tool_messages))

    for tool_msg in tool_messages:
        try:
            executed_call = convert_tool_message_to_executed_call(tool_msg)
            executed_calls.append(executed_call)
            logger.debug("📞 Converted tool call: %s", executed_call.function)
        except Exception as e:
            logger.warning("⚠️ Failed to convert tool message: %s", e)
            # Add a fallback executed call with error information
            fallback_call = ExecutedToolCall(
                function=getattr(tool_msg, "name", "unknown"),
                error=f"Failed to convert tool message: {e}",
            )
            executed_calls.append(fallback_call)

    return executed_calls


def convert_tool_message_to_executed_call(
    tool_msg: ToolMessage,
) -> ExecutedToolCall:
    """
    Convert a ToolMessage to an ExecutedToolCall object.

    Args:
        tool_msg: LangChain ToolMessage instance

    Returns:
        ExecutedToolCall object with extracted information
    """
    import json

    function_name = tool_msg.name or "unknown"

    # Handle content which might be str or list
    content = tool_msg.content
    if isinstance(content, list):
        # Join list content into a single string for JSON parsing
        content_str = " ".join(str(item) for item in content)
    else:
        content_str = str(content) if content else ""

    # Try to parse the content as JSON to extract structured result
    try:
        result_data = json.loads(content_str) if content_str else {}
    except json.JSONDecodeError:
        # If content is not JSON, treat it as raw content
        result_data = {"raw_content": content_str}

    # Extract parameters if available from tool_call_id or other attributes
    params = {}
    if hasattr(tool_msg, "tool_call_id"):
        params["tool_call_id"] = tool_msg.tool_call_id

    return ExecutedToolCall(
        function=function_name,
        params=params,
        result=result_data,
    )
