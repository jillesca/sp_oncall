from dataclasses import field, replace, dataclass
from typing import Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langchain_core.language_models import BaseChatModel

from util.llm import load_chat_model
from util.plans import load_plans, plans_to_string
from configuration import Configuration
from prompts.planner import PLANNER_PROMPT
from schemas.state import Investigation, GraphState
from src.logging import get_logger, log_node_execution
from nodes.markdown_builder import MarkdownBuilder

logger = get_logger(__name__)


@dataclass
class DevicePlan:
    device_name: str
    role: str = ""
    objective: Optional[str] = None
    working_plan_steps: str = ""


@dataclass
class PlanningResponse:
    plan: List[DevicePlan]

    def __len__(self) -> int:
        """Return the number of devices."""
        return len(self.plan)

    def __iter__(self):
        """Make PlanningResponse iterable."""
        return iter(self.plan)


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
        model = _load_model()
        investigations_summary = _extract_investigations_summary(
            state.investigations
        )
        response = _execute_plan_selection(
            model, user_query, available_plans, investigations_summary
        )
        planning_response = _process_planning_response(
            response_content=response, model=model
        )

        logger.debug("📋 PlanningResponse: %s", planning_response)

        return _build_successful_planning_state(
            state,
            planning_response,
        )

    except Exception as e:
        logger.error("❌ Plan generation failed: %s", e)
        return _build_failed_planning_state(state, e)


def _load_available_plans() -> str:
    """Load available plans from the plan repository and format them as string."""
    plans = load_plans()
    available_plans_string = plans_to_string(plans)
    logger.debug("📚 Loaded %s available plans", len(plans))
    return available_plans_string


def _load_model():
    """Setup and return the LLM model for plan selection."""
    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)
    logger.debug("🤖 Using model: %s", configuration.model)
    return model


def _execute_plan_selection(
    model: BaseChatModel,
    user_query: str,
    available_plans: str,
    investigations_summary: str,
) -> BaseMessage:
    """
    Execute plan selection using the LLM.

    Args:
        model: LLM model for structured output
        user_query: The user's query for planning
        available_plans: Formatted string containing all available plans
        investigations_summary: Summary of devices and profiles under investigation

    Returns:
        LLM response with plan selection
    """
    logger.debug("🚀 Invoking LLM for plan selection")

    messages = [
        SystemMessage(content=PLANNER_PROMPT),
        HumanMessage(content=f"request: {user_query}"),
        HumanMessage(content=f"#available_plans:\n{available_plans}"),
        HumanMessage(content=f"#investigations:\n{investigations_summary}"),
    ]
    response = model.invoke(input=messages)

    logger.debug("📨 LLM plan selection response received")
    logger.debug("  Response: %s", response)
    return response


def _process_planning_response(
    response_content: BaseMessage, model: BaseChatModel
) -> PlanningResponse:
    """
    Process LLM response and extract objective and working plan steps.

    Args:
        response: LLM response from plan selection

    Returns:
        Tuple of (objective, working_plan_steps)
    """
    logger.debug("🧠 Getting structured output")

    try:
        # Use the model to process the response and extract device names
        response = model.with_structured_output(
            schema=PlanningResponse
        ).invoke(input=response_content.content)

        # Debug capture for structured output analysis
        logger.debug("📋 Structured output captured: %s", response)

        # Ensure we have a proper InvestigationList object
        if isinstance(response, PlanningResponse):
            return response
        elif isinstance(response, dict) and "plan" in response:
            # Handle case where response is a dict with the expected structure
            investigations_data = response["plan"]
            plan = [
                (
                    DevicePlan(
                        device_name=item["device_name"],
                        objective=item["objective"],
                        working_plan_steps=item["working_plan_steps"],
                    )
                    if isinstance(item, dict)
                    else item
                )
                for item in investigations_data
            ]
            return PlanningResponse(plan=plan)
        else:
            logger.error("❌ Unexpected response format: %s", type(response))
            return PlanningResponse(plan=[])

    except Exception as e:
        logger.error("❌ LLM processing failed: %s", e)
        return PlanningResponse(plan=[])


def _extract_investigations_summary(
    investigations: List[Investigation],
) -> str:
    """
    Extract relevant investigation data for LLM planning context in markdown format.

    Creates a copy of essential investigation information to avoid state mutation
    and provides only the necessary context for plan selection in a structured
    markdown format that enhances LLM comprehension.

    Args:
        investigations: List of Investigation objects from the state

    Returns:
        Markdown-formatted string containing device names and profiles for each investigation
    """
    if not investigations:
        return (
            MarkdownBuilder()
            .add_section("Investigations")
            .add_text("No investigations defined.")
            .build()
        )

    builder = MarkdownBuilder().add_section("Devices")

    for i, investigation in enumerate(investigations, 1):
        # Device header with numbering
        builder.add_subsection(f"{i}. Device: `{investigation.device_name}`")

        # Device profile section
        builder.add_bold_text("Device Profile:")
        builder.add_bold_text("Role:", investigation.role)
        builder.add_code_block(investigation.device_profile)

    logger.debug(
        "📊 Extracted markdown summary for %s devices",
        len(investigations),
    )
    return builder.build()


def _build_successful_planning_state(
    state: GraphState, planning_response: PlanningResponse
) -> GraphState:
    """
    Build GraphState for successful planning.

    Updates Investigation objects with planning data by matching device names.
    Creates a new GraphState with updated Investigation objects using immutable operations.

    Args:
        state: Current GraphState
        planning_response: PlanningResponse containing device-specific plans

    Returns:
        Updated GraphState with planning results applied to matching investigations
    """
    logger.debug("🏗️ Building successful planning state")

    # Create a mapping of device plans for efficient lookup
    device_plans_map = {
        plan.device_name: plan for plan in planning_response.plan
    }

    # Update investigations with planning data
    updated_investigations = []
    for investigation in state.investigations:
        device_plan = device_plans_map.get(investigation.device_name)
        if device_plan:
            # Update investigation with planning data using replace
            updated_investigation = replace(
                investigation,
                objective=device_plan.objective,
                working_plan_steps=device_plan.working_plan_steps,
            )
            updated_investigations.append(updated_investigation)
            logger.debug(
                "📝 Updated investigation for device: %s",
                investigation.device_name,
            )
        else:
            # Keep investigation unchanged if no plan found
            updated_investigations.append(investigation)
            logger.debug(
                "⚠️ No plan found for device: %s", investigation.device_name
            )

    return replace(state, investigations=updated_investigations)


def _build_failed_planning_state(
    state: GraphState, error: Exception
) -> GraphState:
    """
    Build GraphState for failed planning.

    Updates Investigation objects with error information when planning fails.
    Creates a new GraphState with updated Investigation objects using immutable operations.

    Args:
        state: Current GraphState
        error: Exception that occurred during planning

    Returns:
        Updated GraphState with error information applied to investigations
    """
    logger.debug("🏗️ Building failed planning state due to error: %s", error)

    error_objective = (
        f"Planning Error: Failed to generate plan for device - {error}"
    )
    error_working_plan_steps = "Planning failed. Manual intervention required."

    # Update all investigations with error information
    updated_investigations = []
    for investigation in state.investigations:
        updated_investigation = replace(
            investigation,
            objective=error_objective,
            working_plan_steps=error_working_plan_steps,
            error_details=str(error),
        )
        updated_investigations.append(updated_investigation)
        logger.debug(
            "❌ Updated investigation with error for device: %s",
            investigation.device_name,
        )

    return replace(state, investigations=updated_investigations)
