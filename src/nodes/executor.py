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

    Executes a complete investigation of a device using an LLM that can call
    multiple MCP tools in sequence to fulfill the working plan steps.

    Args:
        state: The current GraphState from the workflow

    Returns:
        Updated GraphState with execution results
    """
    device_name = state.device_name
    logger.info("🔧 Executing network commands on device: %s", device_name)

    # Debug: Log incoming state
    logger.debug(
        "📥 Executor received state: device_name='%s', objective='%s', "
        "working_plan_steps=%s steps, "
        "execution_results=%s previous results, retries=%s",
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

    # Determine if this is a retry and add feedback to prompt if so
    retry_context = ""
    if state.current_retries > 0 and state.assessor_feedback_for_retry:
        retry_context = (
            f"\nThis is retry #{state.current_retries}. "
            f"Previous execution feedback: {state.assessor_feedback_for_retry}"
        )
        logger.debug("🔄 Retry context: %s", state.assessor_feedback_for_retry)

    logger.debug("🏗️ Building system prompt for device: %s", device_name)
    system_prompt = (
        f"Execute the following network operations plan for {state.device_name}\n"
        f"Device name: {state.device_name}\n"
        f"IMPORTANT: Focus ONLY on device {state.device_name} - do not attempt to gather information from any other devices.\n"
        f"Objective: {state.objective}\n\n"
        f"Your investigation plan:"
    ) + retry_context

    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)
    logger.debug("🤖 Using model: %s", configuration.model)

    try:
        # Prepare human message content
        human_message_content = NETWORK_EXECUTOR_PROMPT.format(
            device_name=state.device_name,
            working_plan_steps=state.working_plan_steps,
        )

        logger.debug("📤 Sending to MCP agent:")
        logger.debug("  System prompt: %s...", system_prompt[:200])
        logger.debug(
            "  Human message length: %s characters", len(human_message_content)
        )
        logger.debug(
            "  Human message preview: %s...", human_message_content[:300]
        )

        logger.info("🚀 Calling MCP agent for device %s", device_name)
        mcp_response = asyncio.run(
            mcp_node(
                messages=HumanMessage(content=human_message_content),
                system_prompt=system_prompt,
            )
        )

        logger.debug("📨 MCP agent response received: %s", type(mcp_response))
        logger.debug(
            "📨 MCP response keys: %s",
            (
                list(mcp_response.keys())
                if isinstance(mcp_response, dict)
                else "Not a dict"
            ),
        )

        # Handle the response properly - messages should be a list
        messages = mcp_response.get("messages", [])
        logger.debug("📨 MCP response contains %s messages", len(messages))

        if messages and hasattr(messages[-1], "content"):
            response_content = messages[-1].content
            logger.debug(
                "📨 Response content length: %s characters",
                len(str(response_content)),
            )
            logger.debug(
                "📨 Response content preview: %s...",
                str(response_content)[:500],
            )
        else:
            logger.error("❌ No valid response content found in MCP response")
            raise ValueError("No valid response content found")

        logger.debug("🔍 Extracting structured output from response")
        extraction_result = model.with_structured_output(
            schema=StepExecutionResult
        ).invoke(input=response_content)

        logger.debug("🔍 Extraction result type: %s", type(extraction_result))

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

        # Debug: Log extracted data
        logger.debug("📊 Extracted data:")
        logger.debug(
            "  Investigation report length: %s characters",
            len(investigation_report),
        )
        logger.debug("  Executed calls count: %s", len(executed_calls))
        logger.debug("  Tools limitations: %s", tools_limitations)

        if executed_calls:
            logger.debug("📞 Executed calls details:")
            for i, call in enumerate(executed_calls, 1):
                logger.debug("  Call %s: %s", i, call)

        # Create properly typed StepExecutionResult
        step_result = StepExecutionResult(
            investigation_report=investigation_report,
            executed_calls=executed_calls,
            tools_limitations=tools_limitations,
        )

        new_execution_results = state.execution_results + [step_result]

        # Debug: Log state changes
        logger.debug("📤 State changes:")
        logger.debug(
            "  Previous execution_results count: %s",
            len(state.execution_results),
        )
        logger.debug(
            "  New execution_results count: %s", len(new_execution_results)
        )
        logger.debug(
            "  Added result: investigation_report=%s chars, "
            "executed_calls=%s calls",
            len(investigation_report),
            len(executed_calls),
        )

        logger.info("✅ Command execution successful on %s", device_name)
        logger.debug(
            "📈 Execution summary: %s commands executed, "
            "report length: %s characters",
            len(executed_calls),
            len(investigation_report),
        )

        updated_state = replace(state, execution_results=new_execution_results)

        # Debug: Verify state update
        logger.debug("📥 Final state verification:")
        logger.debug(
            "  Final execution_results count: %s",
            len(updated_state.execution_results),
        )
        logger.debug("  Device name: %s", updated_state.device_name)
        logger.debug("  Objective: %s", updated_state.objective)

        return updated_state

    except Exception as e:
        logger.error("❌ Command execution failed on %s: %s", device_name, e)
        logger.error("❌ Exception type: %s", type(e).__name__)
        logger.error("❌ Exception details: %s", str(e))

        # Create properly typed error result
        error_result = StepExecutionResult(
            investigation_report=f"Error executing plan: {e}",
            executed_calls=[],
            tools_limitations=f"Execution failed with error: {e}",
        )

        new_execution_results = state.execution_results + [error_result]

        logger.debug("📤 Error state changes:")
        logger.debug("  Added error result to execution_results")
        logger.debug(
            f"  New execution_results count: {len(new_execution_results)}"
        )

        return replace(state, execution_results=new_execution_results)
