from dataclasses import replace
from typing import Any, Tuple, List
from langchain_core.messages import SystemMessage

from util.llm import load_chat_model
from util.plans import load_plan_data
from configuration import Configuration
from prompts.planner import PLANNER_PROMPT, MULTI_INVESTIGATION_PLANNER_PROMPT
from schemas import GraphState, PlannerOutput
from schemas.state import Investigation, InvestigationStatus

# Add logging
from src.logging import get_logger, log_node_execution

logger = get_logger(__name__)


@log_node_execution("Multi-Investigation Planner")
def multi_investigation_planner_node(state: GraphState) -> GraphState:
    """
    Multi-Investigation Planner node for the new investigation workflow.

    This function orchestrates planning for multiple device investigations by:
    1. Iterating over pending investigations
    2. Creating device-specific plans using device profile and context
    3. Handling cross-investigation dependencies
    4. Updating investigation objectives and working plan steps
    5. Building the updated state with planning results

    Args:
        state: The current GraphState from the workflow with investigations

    Returns:
        Updated GraphState with planned investigations
    """
    logger.info("📋 Planning for %d investigations", len(state.investigations))

    try:
        pending_investigations = state.get_pending_investigations()

        if not pending_investigations:
            logger.info("✅ No pending investigations to plan")
            return state

        available_plans = _load_available_plans()
        model = _setup_planning_model()

        planned_investigations = []
        for investigation in state.investigations:
            if investigation.status == InvestigationStatus.PENDING:
                planned_investigation = _plan_single_investigation(
                    investigation,
                    state.user_query,
                    state.workflow_session,
                    available_plans,
                    model,
                )
                planned_investigations.append(planned_investigation)
            else:
                planned_investigations.append(investigation)

        _log_successful_multi_planning(planned_investigations)
        return _build_successful_multi_planning_state(
            state, planned_investigations
        )

    except Exception as e:
        logger.error("❌ Multi-investigation planning failed: %s", e)
        return _build_failed_multi_planning_state(state, e)


@log_node_execution("Planner")
def planner_node(state: GraphState) -> GraphState:
    """
    Planner node.

    This function orchestrates the planning workflow by:
    1. Loading available plans from the plan repository
    2. Setting up the LLM model for plan selection
    3. Generating a selection prompt with available plans
    4. Processing the LLM response to extract objective and steps
    5. Building the updated state with planning results

    Args:
        state: The current GraphState from the workflow

    Returns:
        Updated GraphState with plan details and selected plan steps
    """
    user_query = state.user_query
    logger.info("📋 Planning for user query: %s", user_query)

    try:
        available_plans = _load_available_plans()
        model = _setup_planning_model()
        system_message = _build_planning_prompt(user_query, available_plans)
        response = _execute_plan_selection(model, system_message)
        objective, working_plan_steps = _process_planning_response(response)

        _log_successful_planning(objective, working_plan_steps)
        return _build_successful_planning_state(
            state, objective, working_plan_steps
        )

    except Exception as e:
        logger.error("❌ Plan generation failed: %s", e)
        return _build_failed_planning_state(state, e)


def _load_available_plans() -> Any:
    """Load available plans from the plan repository."""
    available_plans = load_plan_data()
    logger.debug("📚 Loaded %s available plans", len(available_plans))
    return available_plans


def _setup_planning_model():
    """Setup and return the LLM model for plan selection."""
    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)
    logger.debug("🤖 Using model: %s", configuration.model)
    return model


def _build_planning_prompt(user_query: str, available_plans: Any) -> str:
    """
    Build the planning prompt for LLM plan selection.

    Args:
        user_query: The user's input query
        available_plans: Available plans data

    Returns:
        Formatted system message for plan selection
    """
    logger.debug("🏗️ Generating plan selection prompt")

    system_message = PLANNER_PROMPT.format(
        user_query=user_query, available_plans=available_plans
    )

    logger.debug("📤 Plan selection prompt generated")
    return system_message


def _execute_plan_selection(model, system_message: str) -> Any:
    """
    Execute plan selection using the LLM.

    Args:
        model: LLM model for structured output
        system_message: Formatted planning prompt

    Returns:
        LLM response with plan selection
    """
    logger.debug("🚀 Invoking LLM for plan selection")

    response = model.with_structured_output(schema=PlannerOutput).invoke(
        input=[SystemMessage(content=system_message)]
    )

    logger.debug("📨 LLM plan selection response received")
    return response


def _process_planning_response(response: Any) -> Tuple[str, List[Any]]:
    """
    Process LLM response and extract objective and working plan steps.

    Args:
        response: LLM response from plan selection

    Returns:
        Tuple of (objective, working_plan_steps)
    """
    objective, working_plan_steps = _extract_planner_response(response)

    logger.debug("🔍 Extracted planning data:")
    logger.debug("  Objective: %s", objective)
    logger.debug("  Steps count: %s", len(working_plan_steps))

    return objective, working_plan_steps


def _log_successful_planning(
    objective: str, working_plan_steps: List[Any]
) -> None:
    """Log successful plan generation details."""
    logger.info(
        "✅ Plan generation successful - Selected plan with %s steps",
        len(working_plan_steps),
    )
    logger.debug("📋 Objective: %s", objective)


def _build_successful_planning_state(
    state: GraphState, objective: str, working_plan_steps: List[Any]
) -> GraphState:
    """
    Build GraphState for successful planning.

    Args:
        state: Current GraphState
        objective: Extracted objective
        working_plan_steps: Extracted working plan steps

    Returns:
        Updated GraphState with planning results
    """
    logger.debug("🏗️ Building successful planning state")

    return replace(
        state, objective=objective, working_plan_steps=working_plan_steps
    )


def _build_failed_planning_state(
    state: GraphState, error: Exception
) -> GraphState:
    """
    Build GraphState for failed planning.

    Args:
        state: Current GraphState
        error: Exception that occurred during planning

    Returns:
        Updated GraphState with error information
    """
    logger.debug("🏗️ Building failed planning state due to error: %s", error)

    objective = (
        f"Tool Error: Error extracting device name from user query: {error}"
    )
    working_plan_steps = []

    return replace(
        state, objective=objective, working_plan_steps=working_plan_steps
    )


def _extract_planner_response(response: Any) -> Tuple[str, List[Any]]:
    """
    Extract objective and steps from various LLM response formats.

    This pure function handles different response types that might be returned
    from the LLM, normalizing them into a consistent format.

    Args:
        response: The response from the LLM, which can be:
                 - PlannerOutput dataclass
                 - Object with objective and steps attributes
                 - Dictionary with objective and steps keys
                 - Any other type (fallback)

    Returns:
        Tuple containing:
        - objective (str): The extracted objective or default message
        - working_plan_steps (List[Any]): The extracted steps or empty list
    """
    default_objective = "No objective defined in plan."

    if isinstance(response, PlannerOutput):
        # Direct dataclass response
        objective = response.objective or default_objective
        working_plan_steps = response.steps or []
    elif hasattr(response, "objective") and hasattr(response, "steps"):
        # Structured object with attributes
        objective = getattr(response, "objective", default_objective)
        working_plan_steps = getattr(response, "steps", [])
    elif isinstance(response, dict):
        # Fallback for dict-style responses
        objective = response.get("objective", default_objective)
        working_plan_steps = response.get("steps", [])
    else:
        # Unknown response type
        objective = default_objective
        working_plan_steps = []

    return objective, working_plan_steps


def _plan_single_investigation(
    investigation: Investigation,
    user_query: str,
    workflow_session,
    available_plans: Any,
    model,
) -> Investigation:
    """
    Plan a single investigation for a specific device.

    Args:
        investigation: Investigation object to plan
        user_query: Original user query for context
        workflow_session: Historical context for planning
        available_plans: Available plan templates
        model: LLM model for plan generation

    Returns:
        Updated Investigation with objective and working plan steps
    """
    logger.debug(
        "📋 Planning investigation for device: %s", investigation.device_name
    )

    # Build context for this specific investigation
    session_context = ""
    if workflow_session:
        session_context = f"Session ID: {workflow_session.session_id}, Previous patterns: {len(workflow_session.learned_patterns)}"

    # Format the planning prompt with investigation-specific context
    planning_prompt = MULTI_INVESTIGATION_PLANNER_PROMPT.format(
        user_query=user_query,
        device_name=investigation.device_name,
        device_profile=investigation.device_profile or "unknown",
        priority=investigation.priority.value,
        dependencies=(
            ", ".join(investigation.dependencies)
            if investigation.dependencies
            else "none"
        ),
        session_context=session_context,
        available_plans=available_plans,
    )

    # Execute planning with LLM
    response = model.with_structured_output(schema=PlannerOutput).invoke(
        input=[SystemMessage(content=planning_prompt)]
    )

    # Extract objective and steps
    objective, working_plan_steps = _extract_planner_response(response)

    # Update the investigation with planning results
    updated_investigation = replace(
        investigation,
        objective=objective,
        working_plan_steps=working_plan_steps,
    )

    logger.debug(
        "✅ Planned %d steps for device %s",
        len(working_plan_steps),
        investigation.device_name,
    )
    return updated_investigation


def _log_successful_multi_planning(
    planned_investigations: List[Investigation],
) -> None:
    """Log successful multi-investigation planning details."""
    total_steps = sum(
        len(inv.working_plan_steps) for inv in planned_investigations
    )

    logger.info(
        "✅ Multi-investigation planning successful - %d investigations planned",
        len(planned_investigations),
    )
    logger.info("📊 Total steps across all investigations: %d", total_steps)

    for inv in planned_investigations:
        if (
            inv.status == InvestigationStatus.PENDING
            and inv.working_plan_steps
        ):
            logger.debug(
                "📋 %s: %d steps planned",
                inv.device_name,
                len(inv.working_plan_steps),
            )


def _build_successful_multi_planning_state(
    state: GraphState, planned_investigations: List[Investigation]
) -> GraphState:
    """
    Build GraphState for successful multi-investigation planning.

    Args:
        state: Current GraphState
        planned_investigations: List of planned investigations

    Returns:
        Updated GraphState with planned investigations
    """
    logger.debug("🏗️ Building successful multi-planning state")

    return replace(state, investigations=planned_investigations)


def _build_failed_multi_planning_state(
    state: GraphState, error: Exception
) -> GraphState:
    """
    Build GraphState for failed multi-investigation planning.

    Args:
        state: Current GraphState
        error: Exception that occurred during planning

    Returns:
        Updated GraphState with error information
    """
    logger.debug(
        "🏗️ Building failed multi-planning state due to error: %s", error
    )

    # Mark all pending investigations as failed due to planning error
    failed_investigations = []
    for investigation in state.investigations:
        if investigation.status == InvestigationStatus.PENDING:
            failed_investigation = replace(
                investigation,
                status=InvestigationStatus.FAILED,
                error_details=f"Planning failed: {error}",
                objective=f"Planning Error: Failed to create investigation plan - {error}",
            )
            failed_investigations.append(failed_investigation)
        else:
            failed_investigations.append(investigation)

    return replace(state, investigations=failed_investigations)
