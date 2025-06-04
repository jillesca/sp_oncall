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
    # Default MCP client configuration
    default_config = {
        "gNMIBuddy": {
            "command": "uv",
            "args": [
                "run",
                "--with",
                "mcp[cli],pygnmi,networkx",
                "mcp",
                "run",
                "~/DevNet/cisco_live/25clus/tmp-ai-sp-tools/mcp_server.py",
            ],
            "transport": "stdio",
            "env": {
                "NETWORK_INVENTORY": "/Users/jillesca/DevNet/cisco_live/25clus/tmp-ai-sp-tools/hosts.json"
            },
        },
    }

    mcp_config = client_config or default_config
    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)

    async with MultiServerMCPClient(mcp_config) as client:
        agent = create_react_agent(
            model=model,
            tools=client.get_tools(),
            prompt=system_prompt,
        )

        response = await agent.ainvoke(messages)
        return response
