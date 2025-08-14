import asyncio
from langchain_core.messages import HumanMessage

from sp_oncall.mcp_node import mcp_node
from sp_oncall.util.llm import load_chat_model
from sp_oncall.configuration import Configuration
from prompts.network_executor import NETWORK_EXECUTOR_PROMPT
from sp_oncall.schemas import GraphState, StepExecutionResult


def llm_network_executor(graph_state: GraphState) -> GraphState:
    """
    Network Executor node for the LangGraph workflow.

    Takes the working plan steps from the state and executes them using mcp tools.
    Records execution results and any tool limitations in the state.

    Args:
        graph_state: The current graph state

    Returns:
        Updated graph state with execution results
    """
    retry_context = ""
    if graph_state.get("current_retries", 0) > 0 and graph_state.get(
        "assessor_feedback_for_retry"
    ):
        retry_context = (
            f"\nThis is retry #{graph_state['current_retries']}. "
            f"Previous execution feedback: {graph_state['assessor_feedback_for_retry']}"
        )

    # Create the user message
    user_message = (
        f"Execute the following network operations plan for {graph_state['device_name']}\n"
        f"Device name: {graph_state['device_name']}\n"
        f"IMPORTANT: Focus ONLY on device {graph_state['device_name']} - do not attempt to gather information from any other devices.\n"
        f"Objective: {graph_state['objective']}\n\n"
    )

    if retry_context:
        user_message += f"\n{retry_context}"

    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)

    try:
        mcp_response = asyncio.run(
            mcp_node(
                messages=HumanMessage(content=user_message),
                system_prompt=NETWORK_EXECUTOR_PROMPT.format(
                    device_name=graph_state["device_name"],
                    working_plan_steps=graph_state["working_plan_steps"],
                ),
            )
        )

        response_content = mcp_response.get("messages", "failed")[-1].content

        extraction_result = model.with_structured_output(
            StepExecutionResult
        ).invoke(response_content)

        investigation_report = extraction_result.get(
            "investigation_report", None
        )
        executed_calls = extraction_result.get("executed_calls", None)
        tools_limitations = extraction_result.get("tools_limitations", None)

        graph_state["execution_results"].append(
            {
                "investigation_report": investigation_report,
                "executed_calls": executed_calls,
                "tools_limitations": tools_limitations,
            }
        )

    except Exception as e:
        graph_state["execution_results"] = [
            f"error executing plan. error: {e}"
        ]

    return graph_state
