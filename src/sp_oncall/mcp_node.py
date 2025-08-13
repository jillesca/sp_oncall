from typing import (
    Dict,
    List,
    Optional,
    Any,
    Type,
    TypeVar,
    Union,
)

from langchain_core.messages import AIMessage, HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

from sp_oncall.configuration import Configuration
from sp_oncall.utils import load_chat_model

T = TypeVar("T")


async def mcp_node(
    messages: HumanMessage,
    client_config: Optional[Dict[str, Any]] = None,
    system_prompt: str = None,
) -> Union[Dict[str, List[AIMessage]], T]:
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
    mcp_config = configuration.mcp_client_config or client_config

    client = MultiServerMCPClient(mcp_config)

    tools = await client.get_tools()

    agent = create_react_agent(
        model=model,
        tools=tools,
        prompt=system_prompt,
    )

    return await agent.ainvoke(messages)
