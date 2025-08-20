import asyncio
from dataclasses import replace
from typing import List, Tuple
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from mcp_client import mcp_node
from util.llm import load_chat_model
from configuration import Configuration
from schemas import (
    GraphState,
    ExecutedToolCall,
    Investigation,
    InvestigationStatus,
)
from prompts.network_executor import NETWORK_EXECUTOR_PROMPT

from src.logging import get_logger, log_node_execution

logger = get_logger(__name__)


@log_node_execution("Network Executor")
def llm_network_executor(state: GraphState) -> GraphState:
    """
    Execute network operations for multiple device investigations concurrently.

    This function orchestrates the complete investigation workflow by:
    1. Identifying pending investigations ready for execution
    2. Building appropriate prompts for each device investigation
    3. Executing commands concurrently via MCP agent
    4. Processing and structuring the responses
    5. Updating the workflow state with execution results

    Args:
        state: The current GraphState from the workflow

    Returns:
        Updated GraphState with execution results for all investigations
    """

    _log_incoming_state(state)

    try:
        # Get investigations ready for execution
        ready_investigations = state.get_ready_investigations()

        if not ready_investigations:
            logger.info("🔍 No investigations ready for execution")
            return state

        logger.info(
            "🚀 Starting execution for %s investigations",
            len(ready_investigations),
        )

        # Execute all investigations concurrently
        updated_investigations = asyncio.run(
            _execute_investigations_concurrently(ready_investigations, state)
        )

        # Update state with completed investigations
        return _update_state_with_investigations(state, updated_investigations)

    except Exception as e:
        logger.error("❌ Executor failed: %s", e)
        return _update_state_with_global_error(state, e)


def _log_incoming_state(state: GraphState) -> None:
    """Log incoming state information for debugging purposes."""
    logger.debug(
        "📥 Executor received state: user_query='%s', investigations=%s total, "
        "ready_investigations=%s, current_retries=%s",
        state.user_query,
        len(state.investigations),
        len(state.get_ready_investigations()),
        state.current_retries,
    )

    ready_investigations = state.get_ready_investigations()
    if ready_investigations:
        logger.debug("📋 Ready investigations:")
        for i, investigation in enumerate(ready_investigations, 1):
            logger.debug(
                "  Investigation %s: device=%s, status=%s, objective='%s'",
                i,
                investigation.device_name,
                investigation.status,
                investigation.objective or "Not specified",
            )

    if state.workflow_session:
        logger.debug(
            "📚 Workflow session context available: %s previous reports",
            len(state.workflow_session.previous_reports),
        )

    if state.current_retries > 0:
        logger.warning(
            "🔄 Retry execution #%s for workflow",
            state.current_retries,
        )


def _load_model():
    """Setup and return the LLM model for plan selection."""
    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)
    logger.debug("🤖 Using model: %s", configuration.model)
    return model


async def _execute_investigations_concurrently(
    investigations: List[Investigation], state: GraphState
) -> List[Investigation]:
    """
    Execute multiple investigations concurrently and return updated investigations.

    Args:
        investigations: List of investigations ready for execution
        state: Current GraphState for workflow context

    Returns:
        List of updated Investigation objects with execution results
    """
    logger.info(
        "🚀 Starting concurrent execution for %s investigations",
        len(investigations),
    )

    # Create tasks for concurrent execution
    tasks = []
    for investigation in investigations:
        task = _execute_single_investigation(investigation, state)
        tasks.append(task)

    # Execute all investigations concurrently
    completed_investigations = await asyncio.gather(
        *tasks, return_exceptions=True
    )

    # Process results and handle any exceptions
    updated_investigations = []
    for i, result in enumerate(completed_investigations):
        if isinstance(result, Exception):
            logger.error(
                "❌ Investigation failed for %s: %s",
                investigations[i].device_name,
                result,
            )
            # Create a failed investigation
            failed_investigation = replace(
                investigations[i],
                status=InvestigationStatus.FAILED,
                error_details=str(result),
            )
            updated_investigations.append(failed_investigation)
        else:
            updated_investigations.append(result)

    logger.info("✅ Completed %s investigations", len(updated_investigations))
    return updated_investigations


async def _execute_single_investigation(
    investigation: Investigation, state: GraphState
) -> Investigation:
    """
    Execute a single investigation using the MCP agent.

    Args:
        investigation: Investigation to execute
        state: Current GraphState for workflow context

    Returns:
        Updated Investigation with execution results
    """
    logger.info(
        "🔍 Executing investigation for device: %s", investigation.device_name
    )

    try:
        # Build context for this investigation
        context = _build_investigation_context(investigation, state)
        message = HumanMessage(content=context)

        logger.debug(
            "📤 Sending to MCP agent for device %s", investigation.device_name
        )
        logger.debug("  context length: %s characters", len(context))

        # Execute via MCP agent
        mcp_response = await mcp_node(
            message=message,
            system_prompt=NETWORK_EXECUTOR_PROMPT,
        )

        logger.debug(
            "📨 MCP agent response received for %s", investigation.device_name
        )

        # Process the response
        llm_analysis, executed_tool_calls = _extract_response_content(
            mcp_response
        )

        _log_processed_data(llm_analysis, executed_tool_calls)

        # Update investigation with results
        updated_investigation = replace(
            investigation,
            status=InvestigationStatus.COMPLETED,
            execution_results=investigation.execution_results
            + executed_tool_calls,
            report=llm_analysis,  # Store the investigation report
        )

        logger.info(
            "✅ Investigation completed for device: %s",
            investigation.device_name,
        )
        return updated_investigation

    except Exception as e:
        logger.error(
            "❌ Investigation failed for device %s: %s",
            investigation.device_name,
            e,
        )
        return replace(
            investigation,
            status=InvestigationStatus.FAILED,
            error_details=str(e),
        )


def _build_investigation_context(
    investigation: Investigation, state: GraphState
) -> str:
    """
    Build context string for a specific investigation.

    Args:
        investigation: Investigation to build context for
        state: Current GraphState for workflow context

    Returns:
        Formatted context string for the MCP agent
    """
    context_parts = [
        f"User query: {state.user_query}",
        f"device_name: {investigation.device_name}",
        f"device_profile: {investigation.device_profile}",
        f"role: {investigation.role}",
        f"objective: {investigation.objective}",
        f"working_plan_steps: {investigation.working_plan_steps}",
    ]

    # Add workflow session context if available
    if state.workflow_session:
        context_parts.append("\n--- PREVIOUS INVESTIGATION CONTEXT ---")
        if state.workflow_session.previous_reports:
            context_parts.append("Previous investigation reports:")
            for i, report in enumerate(
                state.workflow_session.previous_reports, 1
            ):
                context_parts.append(f"Report {i}: {report}")

        if state.workflow_session.learned_patterns:
            context_parts.append(
                f"Learned patterns: {state.workflow_session.learned_patterns}"
            )

        if state.workflow_session.device_relationships:
            context_parts.append(
                f"Device relationships: {state.workflow_session.device_relationships}"
            )

    # Add retry context if this is a retry
    if state.current_retries > 0 and state.assessor_feedback_for_retry:
        context_parts.append(f"\n--- RETRY CONTEXT ---")
        context_parts.append(f"This is retry #{state.current_retries}")
        context_parts.append(
            f"Previous execution feedback: {state.assessor_feedback_for_retry}"
        )

    return "\n".join(context_parts)


def _update_state_with_investigations(
    state: GraphState, updated_investigations: List[Investigation]
) -> GraphState:
    """
    Update the GraphState with completed investigations.

    Args:
        state: Current GraphState
        updated_investigations: List of updated investigations

    Returns:
        Updated GraphState
    """
    # Create a mapping of device names to updated investigations
    investigation_map = {
        inv.device_name: inv for inv in updated_investigations
    }

    # Update the investigations list
    updated_investigation_list = []
    for investigation in state.investigations:
        if investigation.device_name in investigation_map:
            # Use the updated investigation
            updated_investigation_list.append(
                investigation_map[investigation.device_name]
            )
        else:
            # Keep the original investigation
            updated_investigation_list.append(investigation)

    logger.info(
        "📊 Updated %s investigations in state", len(updated_investigations)
    )

    return replace(state, investigations=updated_investigation_list)


def _update_state_with_global_error(
    state: GraphState, error: Exception
) -> GraphState:
    """
    Update state with a global error that affects the entire workflow.

    Args:
        state: Current GraphState
        error: Exception that occurred during execution

    Returns:
        Updated GraphState with error information
    """
    logger.error("❌ Global execution error: %s", error)

    # Mark all ready investigations as failed
    updated_investigations = []
    for investigation in state.investigations:
        if investigation.status == InvestigationStatus.PENDING:
            failed_investigation = replace(
                investigation,
                status=InvestigationStatus.FAILED,
                error_details=f"Global execution error: {error}",
            )
            updated_investigations.append(failed_investigation)
        else:
            updated_investigations.append(investigation)

    return replace(state, investigations=updated_investigations)


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

    return ExecutedToolCall(
        function=function_name,
        params=params,
        result=result_data,
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
