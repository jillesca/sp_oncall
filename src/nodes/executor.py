import asyncio
from dataclasses import replace
from langchain_core.messages import HumanMessage

from mcp_client import mcp_node
from util.llm import load_chat_model
from configuration import Configuration
from schemas import GraphState, StepExecutionResult
from prompts.network_executor import NETWORK_EXECUTOR_PROMPT

# Add logging
from src.logging import get_logger, log_operation

logger = get_logger(__name__)


@log_operation("network_command_execution")
def llm_network_executor(state: GraphState) -> GraphState:
    """
    Execute network operations for a specific device using available MCP tools.

    Executes a complete investigation of a device using an LLM that can call
    multiple MCP tools in sequence to fulfill the working plan steps.

    Args:
        state: The current GraphState from the workflow

    Returns:
        Updated GraphState with execution results
    """
    device_name = state.device_name
    logger.info(f"🔧 Executing network commands on device: {device_name}")

    if state.current_retries > 0:
        logger.warning(
            f"🔄 Retry execution #{state.current_retries} for device {device_name}"
        )

    # Determine if this is a retry and add feedback to prompt if so
    retry_context = ""
    if state.current_retries > 0 and state.assessor_feedback_for_retry:
        retry_context = (
            f"\nThis is retry #{state.current_retries}. "
            f"Previous execution feedback: {state.assessor_feedback_for_retry}"
        )
        logger.debug(f"Retry context: {state.assessor_feedback_for_retry}")

    logger.debug(f"Building system prompt for device: {device_name}")
    system_prompt = (
        f"Execute the following network operations plan for {state.device_name}\n"
        f"Device name: {state.device_name}\n"
        f"IMPORTANT: Focus ONLY on device {state.device_name} - do not attempt to gather information from any other devices.\n"
        f"Objective: {state.objective}\n\n"
        f"Your investigation plan:"
    ) + retry_context

    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)
    logger.debug(f"Using model: {configuration.model}")

    try:
        logger.debug("Executing MCP node with network commands")
        mcp_response = asyncio.run(
            mcp_node(
                messages=HumanMessage(
                    content=NETWORK_EXECUTOR_PROMPT.format(
                        device_name=state.device_name,
                        working_plan_steps=state.working_plan_steps,
                    )
                ),
                system_prompt=system_prompt,
            )
        )
        logger.debug("MCP node execution completed")

        # Handle the response properly - messages should be a list
        messages = mcp_response.get("messages", [])
        if messages and hasattr(messages[-1], "content"):
            response_content = messages[-1].content
            logger.debug(
                f"Received response content length: {len(str(response_content))}"
            )
        else:
            raise ValueError("No valid response content found")

        logger.debug("Extracting structured output from response")
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
        step_result = StepExecutionResult(
            investigation_report=investigation_report,
            executed_calls=executed_calls,
            tools_limitations=tools_limitations,
        )

        new_execution_results = state.execution_results + [step_result]

        logger.info(f"✅ Command execution successful on {device_name}")
        logger.debug(
            f"Executed {len(executed_calls)} commands, report length: {len(investigation_report)}"
        )

        return replace(state, execution_results=new_execution_results)

    except Exception as e:
        logger.error(f"❌ Command execution failed on {device_name}: {e}")

        # Create properly typed error result
        error_result = StepExecutionResult(
            investigation_report=f"Error executing plan: {e}",
            executed_calls=[],
            tools_limitations=f"Execution failed with error: {e}",
        )

        new_execution_results = state.execution_results + [error_result]

        return replace(state, execution_results=new_execution_results)
