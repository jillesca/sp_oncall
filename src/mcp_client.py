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

    This function orchestrates the MCP tool execution workflow by:
    1. Logging and validating incoming request details
    2. Setting up the LLM model and MCP configuration
    3. Creating the MCP client and retrieving available tools
    4. Building and executing the reactive agent
    5. Processing and logging the execution results

    Args:
        messages: List of message dicts for the MCP agent.
        client_config: Optional configuration for the MultiServerMCPClient.
        system_prompt: System prompt. must be provided

    Returns:
        Updated state with results from MCP tool execution.
    """
    logger.info("🚀 Starting MCP agent execution")

    _log_incoming_request_details(messages, system_prompt)

    model = _setup_mcp_model()
    mcp_config = await _load_mcp_config(client_config)
    tools = await _setup_mcp_tools(mcp_config)
    result = await _execute_mcp_agent(model, messages, tools, system_prompt)

    _log_execution_results(result)

    logger.info("✅ MCP agent execution completed successfully")
    return result


def _log_incoming_request_details(
    messages: HumanMessage, system_prompt: str
) -> None:
    """Log incoming request details for debugging purposes."""
    logger.debug("📤 MCP agent input:")
    logger.debug("  Message type: %s", type(messages))

    message_content_length = (
        len(str(messages.content))
        if hasattr(messages, "content")
        else "No content"
    )
    logger.debug("  Message content length: %s", message_content_length)
    logger.debug("  System prompt length: %s", len(system_prompt))
    logger.debug("  System prompt preview: %s...", system_prompt[:200])

    message_preview = (
        str(messages.content)[:300]
        if hasattr(messages, "content")
        else "No content"
    )
    logger.debug("  Message content preview: %s...", message_preview)


def _setup_mcp_model():
    """Setup and return the LLM model for MCP execution."""
    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)
    logger.debug("🤖 Using model: %s", configuration.model)
    return model


async def _load_mcp_config(
    client_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Load MCP configuration from various sources.

    Args:
        client_config: Optional client configuration

    Returns:
        MCP configuration dictionary
    """
    configuration = Configuration.from_context()
    mcp_config = await _resolve_mcp_config_source(client_config, configuration)
    logger.debug("⚙️ MCP configuration loaded from: %s", type(mcp_config))
    return mcp_config


async def _resolve_mcp_config_source(
    client_config: Optional[Dict[str, Any]], configuration: Configuration
) -> Dict[str, Any]:
    """Resolve MCP configuration from available sources."""
    if client_config:
        return client_config

    if configuration is not None and getattr(
        configuration, "mcp_client_config", None
    ):
        return configuration.mcp_client_config

    return await load_project_json_async(DEFAULT_MCP_CONFIG_FILENAME)


async def _setup_mcp_tools(mcp_config: Dict[str, Any]) -> List[Any]:
    """
    Setup MCP client and retrieve available tools.

    Args:
        mcp_config: MCP configuration dictionary

    Returns:
        List of available MCP tools
    """
    client = MultiServerMCPClient(mcp_config)
    tools = await client.get_tools()

    logger.info("🛠️ Retrieved %s MCP tools", len(tools))
    _log_available_tools(tools)

    return tools


def _log_available_tools(tools: List[Any]) -> None:
    """Log details of available MCP tools."""
    if tools:
        logger.debug("🛠️ Available MCP tools:")
        for i, tool in enumerate(tools, 1):
            tool_name = getattr(tool, "name", "Unknown")
            logger.debug("  Tool %s: %s", i, tool_name)


async def _execute_mcp_agent(
    model, messages: HumanMessage, tools: List[Any], system_prompt: str
) -> Dict[str, List[AIMessage]]:
    """
    Create a reactive agent with the given model, tools, and prompt.

    Args:
        model: LLM model for the agent
        tools: List of available tools
        system_prompt: System prompt for the agent

    Returns:
        Configured reactive agent
    """
    logger.debug("🤖 Reactive agent created with %s tools", len(tools))

    agent = create_react_agent(
        model=model,
        tools=tools,
        prompt=system_prompt,
    )

    logger.info("🎯 Executing MCP agent with %s tools available", len(tools))
    return await agent.ainvoke(messages)


def _log_execution_results(result: Dict[str, List[AIMessage]]) -> None:
    """Log detailed execution results for debugging purposes."""
    logger.debug("📨 MCP agent execution completed:")
    logger.debug("  Result type: %s", type(result))
    logger.debug(
        "  Result keys: %s",
        list(result.keys()) if isinstance(result, dict) else "Not a dict",
    )

    if isinstance(result, dict):
        _log_result_messages(result)


def _log_result_messages(result: Dict[str, Any]) -> None:
    """Log details of result messages."""
    messages_result = result.get("messages", [])
    logger.debug("  Messages count: %s", len(messages_result))

    if messages_result:
        last_message = messages_result[-1]
        _log_last_message_details(last_message)


def _log_last_message_details(last_message) -> None:
    """Log details of the last message in the result."""
    logger.debug("  Last message type: %s", type(last_message))

    if hasattr(last_message, "content"):
        content_length = len(str(last_message.content))
        logger.debug("  Last message content length: %s", content_length)
        logger.debug(
            "  Last message preview: %s...", str(last_message.content)[:500]
        )

    _log_tool_calls(last_message)


def _log_tool_calls(message) -> None:
    """Log tool calls made by the agent if any."""
    if hasattr(message, "tool_calls") and message.tool_calls:
        logger.info("🔧 MCP agent made %s tool calls", len(message.tool_calls))
        for i, tool_call in enumerate(message.tool_calls, 1):
            tool_name = getattr(tool_call, "name", "Unknown")
            tool_id = getattr(tool_call, "id", "No ID")
            logger.debug("  Tool call %s: %s - %s", i, tool_name, tool_id)
    else:
        logger.debug("🔧 No tool calls detected in response")
