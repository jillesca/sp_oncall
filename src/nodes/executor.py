import asyncio
from langchain_core.messages import HumanMessage

from mcp_client import mcp_node
from util.llm import load_chat_model
from configuration import Configuration
from schemas import GraphState, StepExecutionResult
from prompts.network_executor import NETWORK_EXECUTOR_PROMPT


def llm_network_executor(state: GraphState) -> GraphState:
    """
    Network Executor node for the LangGraph workflow.

    Takes the working plan steps from the state and executes them using mcp tools.
    Records execution results and any tool limitations in the state.

    Args:
        state: The current graph state

    Returns:
        Updated graph state with execution results
    """
    updated_state = state.copy()

    retry_context = ""
    if updated_state.get("current_retries", 0) > 0 and updated_state.get(
        "assessor_feedback_for_retry"
    ):
        retry_context = (
            f"\nThis is retry #{updated_state['current_retries']}. "
            f"Previous execution feedback: {updated_state['assessor_feedback_for_retry']}"
        )

    # Create the user message
    user_message = (
        f"Execute the following network operations plan for {updated_state['device_name']}\n"
        f"Device name: {updated_state['device_name']}\n"
        f"IMPORTANT: Focus ONLY on device {updated_state['device_name']} - do not attempt to gather information from any other devices.\n"
        f"Objective: {updated_state['objective']}\n\n"
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
                    device_name=updated_state["device_name"],
                    working_plan_steps=updated_state["working_plan_steps"],
                ),
            )
        )

        # Handle the response properly - messages should be a list
        messages = mcp_response.get("messages", [])
        if messages and hasattr(messages[-1], "content"):
            response_content = messages[-1].content
        else:
            raise ValueError("No valid response content found")

        extraction_result = model.with_structured_output(
            StepExecutionResult
        ).invoke(response_content)

        # Handle structured output properly - it could be a BaseModel or dict
        if isinstance(extraction_result, dict):
            investigation_report = extraction_result.get(
                "investigation_report", ""
            )
            executed_calls = extraction_result.get("executed_calls", [])
            tools_limitations = extraction_result.get("tools_limitations", "")
        else:
            # Assume it's a structured object with attributes
            investigation_report = getattr(
                extraction_result, "investigation_report", ""
            )
            executed_calls = getattr(extraction_result, "executed_calls", [])
            tools_limitations = getattr(
                extraction_result, "tools_limitations", ""
            )

        # Create properly typed StepExecutionResult
        step_result: StepExecutionResult = {
            "investigation_report": investigation_report,
            "executed_calls": executed_calls,
            "tools_limitations": tools_limitations,
        }

        updated_state["execution_results"].append(step_result)

    except Exception as e:
        # Create properly typed error result
        error_result: StepExecutionResult = {
            "investigation_report": f"Error executing plan: {e}",
            "executed_calls": [],
            "tools_limitations": f"Execution failed with error: {e}",
        }
        updated_state["execution_results"].append(error_result)

    return updated_state
