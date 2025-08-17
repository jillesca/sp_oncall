import asyncio
from dataclasses import replace
from langchain_core.messages import HumanMessage

from mcp_client import mcp_node
from util.llm import load_chat_model
from configuration import Configuration
from schemas import GraphState, StepExecutionResult
from prompts.network_executor import NETWORK_EXECUTOR_PROMPT

# Add logging
from src.logging import get_logger, log_node_execution

logger = get_logger(__name__)


@log_node_execution("Network Executor")
def llm_network_executor(state: GraphState) -> GraphState:
    """
    Execute network operations for a specific device using available MCP tools.
    
    This function orchestrates the complete investigation workflow by:
    1. Validating the current state
    2. Building appropriate prompts for the LLM
    3. Executing commands via MCP agent
    4. Processing and structuring the response
    5. Updating the workflow state
    
    Args:
        state: The current GraphState from the workflow
        
    Returns:
        Updated GraphState with execution results
    """
    device_name = state.device_name
    logger.info("🔧 Executing network commands on device: %s", device_name)
    
    _log_incoming_state(state)
    
    try:
        prompts = _build_execution_prompts(state)
        model = _setup_llm_model()
        
        mcp_response = _execute_via_mcp_agent(prompts, device_name)
        response_content = _extract_response_content(mcp_response)
        step_result = _process_llm_response(response_content, model)
        
        return _update_state_with_success(state, step_result)
        
    except Exception as e:
        logger.error("❌ Command execution failed on %s: %s", device_name, e)
        return _update_state_with_error(state, e)


def _log_incoming_state(state: GraphState) -> None:
    """Log incoming state information for debugging purposes."""
    device_name = state.device_name
    
    logger.debug(
        "📥 Executor received state: device_name='%s', objective='%s', "
        "working_plan_steps=%s steps, execution_results=%s previous results, retries=%s",
        device_name,
        state.objective,
        len(state.working_plan_steps) if state.working_plan_steps else 0,
        len(state.execution_results),
        state.current_retries,
    )

    if state.working_plan_steps:
        logger.debug("📋 Working plan steps to execute:")
        for i, step in enumerate(state.working_plan_steps, 1):
            logger.debug("  Step %s: %s", i, step)

    if state.current_retries > 0:
        logger.warning(
            "🔄 Retry execution #%s for device %s",
            state.current_retries,
            device_name,
        )


def _build_execution_prompts(state: GraphState) -> tuple[str, str]:
    """
    Build system prompt and human message for LLM execution.
    
    Returns:
        Tuple of (system_prompt, human_message_content)
    """
    retry_context = _build_retry_context(state)
    
    system_prompt = (
        f"Execute the following network operations plan for {state.device_name}\n"
        f"Device name: {state.device_name}\n"
        f"IMPORTANT: Focus ONLY on device {state.device_name} - do not attempt to gather information from any other devices.\n"
        f"Objective: {state.objective}\n\n"
        f"Your investigation plan:"
    ) + retry_context

    human_message_content = NETWORK_EXECUTOR_PROMPT.format(
        device_name=state.device_name,
        working_plan_steps=state.working_plan_steps,
    )
    
    logger.debug("🏗️ Built prompts for device: %s", state.device_name)
    logger.debug("  System prompt: %s...", system_prompt[:200])
    logger.debug("  Human message length: %s characters", len(human_message_content))
    
    return system_prompt, human_message_content


def _build_retry_context(state: GraphState) -> str:
    """Build retry context string if this is a retry execution."""
    if state.current_retries > 0 and state.assessor_feedback_for_retry:
        retry_context = (
            f"\nThis is retry #{state.current_retries}. "
            f"Previous execution feedback: {state.assessor_feedback_for_retry}"
        )
        logger.debug("� Retry context: %s", state.assessor_feedback_for_retry)
        return retry_context
    return ""


def _setup_llm_model():
    """Setup and return the LLM model for structured output extraction."""
    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)
    logger.debug("🤖 Using model: %s", configuration.model)
    return model


def _execute_via_mcp_agent(prompts: tuple[str, str], device_name: str) -> dict:
    """
    Execute the investigation plan via MCP agent.
    
    Args:
        prompts: Tuple of (system_prompt, human_message_content)
        device_name: Name of the device being investigated
        
    Returns:
        MCP agent response dictionary
    """
    system_prompt, human_message_content = prompts
    
    logger.debug("📤 Sending to MCP agent:")
    logger.debug("  Human message preview: %s...", human_message_content[:300])
    
    logger.info("🚀 Calling MCP agent for device %s", device_name)
    mcp_response = asyncio.run(
        mcp_node(
            messages=HumanMessage(content=human_message_content),
            system_prompt=system_prompt,
        )
    )
    
    logger.debug("📨 MCP agent response received: %s", type(mcp_response))
    return mcp_response


def _extract_response_content(mcp_response: dict) -> str:
    """
    Extract response content from MCP agent response.
    
    Args:
        mcp_response: Response from MCP agent
        
    Returns:
        Extracted response content as string
        
    Raises:
        ValueError: If no valid response content found
    """
    logger.debug(
        "📨 MCP response keys: %s",
        list(mcp_response.keys()) if isinstance(mcp_response, dict) else "Not a dict",
    )

    messages = mcp_response.get("messages", [])
    logger.debug("📨 MCP response contains %s messages", len(messages))

    if messages and hasattr(messages[-1], "content"):
        response_content = messages[-1].content
        logger.debug("📨 Response content length: %s characters", len(str(response_content)))
        logger.debug("📨 Response content preview: %s...", str(response_content)[:500])
        return response_content
    else:
        logger.error("❌ No valid response content found in MCP response")
        raise ValueError("No valid response content found")


def _process_llm_response(response_content: str, model) -> StepExecutionResult:
    """
    Process LLM response and extract structured data.
    
    Args:
        response_content: Raw response content from MCP agent
        model: LLM model for structured output extraction
        
    Returns:
        Structured StepExecutionResult
    """
    logger.debug("🔍 Extracting structured output from response")
    extraction_result = model.with_structured_output(
        schema=StepExecutionResult
    ).invoke(input=response_content)

    logger.debug("🔍 Extraction result type: %s", type(extraction_result))

    investigation_report, executed_calls, tools_limitations = _extract_result_fields(extraction_result)
    
    _log_extracted_data(investigation_report, executed_calls, tools_limitations)
    
    return StepExecutionResult(
        investigation_report=investigation_report,
        executed_calls=executed_calls,
        tools_limitations=tools_limitations,
    )


def _extract_result_fields(extraction_result) -> tuple[str, list, str]:
    """Extract fields from structured output result, handling both dict and object types."""
    if isinstance(extraction_result, dict):
        investigation_report = extraction_result.get("investigation_report", "")
        executed_calls = extraction_result.get("executed_calls", [])
        tools_limitations = extraction_result.get("tools_limitations", "")
    else:
        investigation_report = getattr(extraction_result, "investigation_report", "")
        executed_calls = getattr(extraction_result, "executed_calls", [])
        tools_limitations = getattr(extraction_result, "tools_limitations", "")
    
    return investigation_report, executed_calls, tools_limitations


def _log_extracted_data(investigation_report: str, executed_calls: list, tools_limitations: str) -> None:
    """Log extracted data for debugging purposes."""
    logger.debug("📊 Extracted data:")
    logger.debug("  Investigation report length: %s characters", len(investigation_report))
    logger.debug("  Executed calls count: %s", len(executed_calls))
    logger.debug("  Tools limitations: %s", tools_limitations)

    if executed_calls:
        logger.debug("📞 Executed calls details:")
        for i, call in enumerate(executed_calls, 1):
            logger.debug("  Call %s: %s", i, call)


def _update_state_with_success(state: GraphState, step_result: StepExecutionResult) -> GraphState:
    """
    Update state with successful execution results.
    
    Args:
        state: Current GraphState
        step_result: Successful execution result
        
    Returns:
        Updated GraphState
    """
    new_execution_results = state.execution_results + [step_result]
    
    _log_state_changes(state, new_execution_results, step_result)
    
    logger.info("✅ Command execution successful on %s", state.device_name)
    logger.debug(
        "📈 Execution summary: %s commands executed, report length: %s characters",
        len(step_result.executed_calls),
        len(step_result.investigation_report),
    )

    updated_state = replace(state, execution_results=new_execution_results)
    _log_final_state_verification(updated_state)
    
    return updated_state


def _update_state_with_error(state: GraphState, error: Exception) -> GraphState:
    """
    Update state with error execution results.
    
    Args:
        state: Current GraphState
        error: Exception that occurred during execution
        
    Returns:
        Updated GraphState with error information
    """
    logger.error("❌ Exception type: %s", type(error).__name__)
    logger.error("❌ Exception details: %s", str(error))

    error_result = StepExecutionResult(
        investigation_report=f"Error executing plan: {error}",
        executed_calls=[],
        tools_limitations=f"Execution failed with error: {error}",
    )

    new_execution_results = state.execution_results + [error_result]

    logger.debug("📤 Error state changes:")
    logger.debug("  Added error result to execution_results")
    logger.debug("  New execution_results count: %s", len(new_execution_results))

    return replace(state, execution_results=new_execution_results)


def _log_state_changes(state: GraphState, new_execution_results: list, step_result: StepExecutionResult) -> None:
    """Log state changes for debugging purposes."""
    logger.debug("📤 State changes:")
    logger.debug("  Previous execution_results count: %s", len(state.execution_results))
    logger.debug("  New execution_results count: %s", len(new_execution_results))
    logger.debug(
        "  Added result: investigation_report=%s chars, executed_calls=%s calls",
        len(step_result.investigation_report),
        len(step_result.executed_calls),
    )


def _log_final_state_verification(updated_state: GraphState) -> None:
    """Log final state verification for debugging purposes."""
    logger.debug("📥 Final state verification:")
    logger.debug("  Final execution_results count: %s", len(updated_state.execution_results))
    logger.debug("  Device name: %s", updated_state.device_name)
    logger.debug("  Objective: %s", updated_state.objective)
