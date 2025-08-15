from typing import (
    Dict,
    List,
    Optional,
    Any,
    TypeVar,
)

from langgraph.prebuilt import create_react_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

from util.llm import load_chat_model
from util.file_loader import load_project_json_async
from configuration import Configuration, DEFAULT_MCP_CONFIG_FILENAME

# Add logging
from src.logging import get_logger, log_operation

logger = get_logger(__name__)

T = TypeVar("T")


@log_operation("mcp_tool_execution")
async def mcp_node(
    messages: HumanMessage,
    client_config: Optional[Dict[str, Any]] = None,
    system_prompt: str = "",
) -> Dict[str, List[AIMessage]]:
    """
    Generic node for executing MCP tools in the LangGraph pipeline.

    Args:
        messages: List of message dicts for the MCP agent.
        client_config: Optional configuration for the MultiServerMCPClient.
        system_prompt: System prompt. must be provided
        response_format: Optional type for structured output. If provided, the agent
                         will be configured to return data in this structure.

    Returns:
        Updated state with results from MCP tool execution or structured output if specified.
    """
    logger.info("🚀 Starting MCP agent execution")

    # Debug: Log incoming request details
    logger.debug("📤 MCP agent input:")
    logger.debug("  Message type: %s", type(messages))
    logger.debug(
        "  Message content length: %s",
        (
            len(str(messages.content))
            if hasattr(messages, "content")
            else "No content"
        ),
    )
    logger.debug("  System prompt length: %s", len(system_prompt))
    logger.debug("  System prompt preview: %s...", system_prompt[:200])
    logger.debug(
        "  Message content preview: %s...",
        (
            str(messages.content)[:300]
            if hasattr(messages, "content")
            else "No content"
        ),
    )

    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)
    logger.debug("🤖 Using model: %s", configuration.model)

    mcp_config = await _load_mcp_config(client_config, configuration)
    logger.debug("⚙️ MCP configuration loaded from: %s", type(mcp_config))

    client = MultiServerMCPClient(mcp_config)
    tools = await client.get_tools()
    logger.info("🛠️ Retrieved %s MCP tools", len(tools))

    # Debug: Log available tools
    if tools:
        logger.debug("🛠️ Available MCP tools:")
        for i, tool in enumerate(tools, 1):
            tool_name = getattr(tool, "name", "Unknown")
            logger.debug("  Tool %s: %s", i, tool_name)

    agent = create_react_agent(
        model=model,
        tools=tools,
        prompt=system_prompt,
    )

    logger.info("🎯 Executing MCP agent with %s tools available", len(tools))
    result = await agent.ainvoke(messages)

    # Debug: Log result details
    logger.debug("📨 MCP agent execution completed:")
    logger.debug("  Result type: %s", type(result))
    logger.debug(
        "  Result keys: %s",
        list(result.keys()) if isinstance(result, dict) else "Not a dict",
    )

    if isinstance(result, dict):
        messages_result = result.get("messages", [])
        logger.debug("  Messages count: %s", len(messages_result))

        if messages_result:
            last_message = messages_result[-1]
            logger.debug("  Last message type: %s", type(last_message))
            if hasattr(last_message, "content"):
                content_length = len(str(last_message.content))
                logger.debug(
                    "  Last message content length: %s", content_length
                )
                logger.debug(
                    "  Last message preview: %s...",
                    str(last_message.content)[:500],
                )

            # Log tool calls if any
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                logger.info(
                    f"🔧 MCP agent made {len(last_message.tool_calls)} tool calls"
                )
                for i, tool_call in enumerate(last_message.tool_calls, 1):
                    logger.debug(
                        f"  Tool call {i}: {getattr(tool_call, 'name', 'Unknown')} - {getattr(tool_call, 'id', 'No ID')}"
                    )
            else:
                logger.debug("🔧 No tool calls detected in response")

    logger.info("✅ MCP agent execution completed successfully")
    return result


async def _load_mcp_config(
    client_config: Optional[Dict[str, Any]] = None,
    configuration: Optional[Configuration] = None,
) -> Dict[str, Any]:
    """Load MCP configuration from various sources."""
    if client_config:
        return client_config

    if configuration is not None and getattr(
        configuration, "mcp_client_config", None
    ):
        return configuration.mcp_client_config

    return await load_project_json_async(DEFAULT_MCP_CONFIG_FILENAME)
