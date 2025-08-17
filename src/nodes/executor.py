import asyncio
from dataclasses import replace
from typing import List, Tuple
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from mcp_client import mcp_node
from util.llm import load_chat_model
from configuration import Configuration
from schemas import GraphState, StepExecutionResult, ExecutedToolCall
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
        llm_analysis, executed_tool_calls = _extract_response_content(
            mcp_response
        )
        step_result = _process_llm_response(llm_analysis, executed_tool_calls)

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
    logger.debug(
        "  Human message length: %s characters", len(human_message_content)
    )

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


def _extract_response_content(
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
    llm_analysis = _extract_last_ai_message(messages)

    # Extract all ToolMessages (contains tool execution results)
    executed_tool_calls = _extract_tool_messages(messages)

    logger.debug(
        "📨 Extracted %s tool calls and LLM analysis (%s chars)",
        len(executed_tool_calls),
        len(llm_analysis),
    )

    return llm_analysis, executed_tool_calls


def _extract_last_ai_message(messages: List) -> str:
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


def _extract_tool_messages(messages: List) -> List[ExecutedToolCall]:
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
            executed_call = _convert_tool_message_to_executed_call(tool_msg)
            executed_calls.append(executed_call)
            logger.debug("📞 Converted tool call: %s", executed_call.function)
        except Exception as e:
            logger.warning("⚠️ Failed to convert tool message: %s", e)
            # Add a fallback executed call with error information
            fallback_call = ExecutedToolCall(
                function=getattr(tool_msg, "name", "unknown"),
                error=f"Failed to convert tool message: {e}",
                detailed_findings="Tool message conversion failed",
            )
            executed_calls.append(fallback_call)

    return executed_calls


def _convert_tool_message_to_executed_call(
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

    # Create detailed findings from the result
    detailed_findings = _create_detailed_findings_from_result(
        result_data, function_name
    )

    return ExecutedToolCall(
        function=function_name,
        params=params,
        result=result_data,
        detailed_findings=detailed_findings,
    )


def _create_detailed_findings_from_result(
    result_data: dict, function_name: str
) -> str:
    """
    Create a human-readable summary of tool execution results.

    Args:
        result_data: Structured result data from tool execution
        function_name: Name of the executed function

    Returns:
        Human-readable detailed findings string
    """
    if not result_data:
        return f"Executed {function_name} - no result data"

    # Extract key information based on common result structure
    device_name = result_data.get("device_name", "unknown")
    status = result_data.get("status", "unknown")
    operation_type = result_data.get("operation_type", function_name)

    findings = (
        f"Executed {function_name} on device {device_name} - Status: {status}"
    )

    # Add summary if available
    if "data" in result_data and isinstance(result_data["data"], dict):
        data = result_data["data"]
        if "summary" in data:
            summary = data["summary"]
            if isinstance(summary, dict) and "summary" in summary:
                findings += f" | Summary: {str(summary['summary'])[:200]}..."
            elif isinstance(summary, str):
                findings += f" | Summary: {summary[:200]}..."

    # Add metadata if available
    if "metadata" in result_data:
        metadata = result_data["metadata"]
        if isinstance(metadata, dict):
            relevant_metadata = []
            for key, value in metadata.items():
                if key in [
                    "total_interfaces",
                    "successful_protocols",
                    "total_vrfs_on_device",
                ]:
                    relevant_metadata.append(f"{key}: {value}")
            if relevant_metadata:
                findings += f" | Metadata: {', '.join(relevant_metadata)}"

    return findings


def _process_llm_response(
    llm_analysis: str, executed_tool_calls: List[ExecutedToolCall]
) -> StepExecutionResult:
    """
    Process LLM analysis and tool execution results into a structured StepExecutionResult.

    Args:
        llm_analysis: The LLM's analysis report from the last AIMessage
        executed_tool_calls: List of ExecutedToolCall objects from ToolMessages

    Returns:
        Structured StepExecutionResult
    """
    logger.debug(
        "🔍 Processing LLM analysis and %s tool calls",
        len(executed_tool_calls),
    )

    # Use the LLM analysis as the investigation report
    investigation_report = llm_analysis

    _log_processed_data(investigation_report, executed_tool_calls)

    return StepExecutionResult(
        investigation_report=investigation_report,
        executed_calls=executed_tool_calls,
    )


def _log_processed_data(
    investigation_report: str,
    executed_tool_calls: List[ExecutedToolCall],
) -> None:
    """Log processed data for debugging purposes."""
    logger.debug("📊 Processed data:")
    logger.debug(
        "  Investigation report length: %s characters",
        len(investigation_report),
    )
    logger.debug("  Executed calls count: %s", len(executed_tool_calls))

    if executed_tool_calls:
        logger.debug("📞 Processed calls details:")
        for i, call in enumerate(executed_tool_calls, 1):
            logger.debug(
                "  Call %s: %s (error: %s)",
                i,
                call.function,
                call.error or "None",
            )


def _update_state_with_success(
    state: GraphState, step_result: StepExecutionResult
) -> GraphState:
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


def _update_state_with_error(
    state: GraphState, error: Exception
) -> GraphState:
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
    )

    new_execution_results = state.execution_results + [error_result]

    logger.debug("📤 Error state changes:")
    logger.debug("  Added error result to execution_results")
    logger.debug(
        "  New execution_results count: %s", len(new_execution_results)
    )

    return replace(state, execution_results=new_execution_results)


def _log_state_changes(
    state: GraphState,
    new_execution_results: list,
    step_result: StepExecutionResult,
) -> None:
    """Log state changes for debugging purposes."""
    logger.debug("📤 State changes:")
    logger.debug(
        "  Previous execution_results count: %s", len(state.execution_results)
    )
    logger.debug(
        "  New execution_results count: %s", len(new_execution_results)
    )
    logger.debug(
        "  Added result: investigation_report=%s chars, executed_calls=%s calls",
        len(step_result.investigation_report),
        len(step_result.executed_calls),
    )


def _log_final_state_verification(updated_state: GraphState) -> None:
    """Log final state verification for debugging purposes."""
    logger.debug("📥 Final state verification:")
    logger.debug(
        "  Final execution_results count: %s",
        len(updated_state.execution_results),
    )
    logger.debug("  Device name: %s", updated_state.device_name)
    logger.debug("  Objective: %s", updated_state.objective)
