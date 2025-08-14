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

from sp_oncall.util.llm import load_chat_model
from sp_oncall.util.file_loader import load_project_json_async
from sp_oncall.configuration import Configuration, DEFAULT_MCP_CONFIG_FILENAME

T = TypeVar("T")


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

    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)
    mcp_config = await _load_mcp_config(client_config, configuration)

    client = MultiServerMCPClient(mcp_config)
    tools = await client.get_tools()

    agent = create_react_agent(
        model=model,
        tools=tools,
        prompt=system_prompt,
    )

    return await agent.ainvoke(messages)


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
