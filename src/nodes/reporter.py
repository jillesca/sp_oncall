from typing import List
from langchain_core.messages import SystemMessage, HumanMessage

from schemas import GraphState, LearningInsights
from schemas.state import Investigation, InvestigationStatus, WorkflowSession
from util.llm import load_chat_model
from configuration import Configuration
from prompts.report_generator import REPORT_GENERATOR_PROMPT
from prompts.learning_insights import LEARNING_INSIGHTS_PROMPT
from .markdown_builder import MarkdownBuilder

# Add logging
from src.logging import get_logger, log_node_execution

logger = get_logger(__name__)


@log_node_execution("Investigation Reporter")
def investigation_report_node(state: GraphState) -> GraphState:
    """
    Generate a comprehensive investigation report and reset workflow state.

    This function orchestrates the complete report generation workflow by:
    1. Building comprehensive context from all investigations
    2. Setting up the LLM model for report generation
    3. Generating the final report using the LLM
    4. Updating workflow session with learned patterns and findings
    5. Resetting GraphState to initial state while preserving WorkflowSession

    Args:
        state: The current GraphState with all investigation results

    Returns:
        Reset GraphState with updated WorkflowSession and final_report populated
    """
    logger.info(
        "📄 Generating comprehensive investigation report for %d devices",
        len(state.investigations),
    )

    try:
        report_context = _build_report_context(state)
        model = _setup_report_model()
        final_report = _generate_report(model, report_context)

        # Update workflow session with the generated final report
        updated_session = _update_workflow_session(state, final_report)

        _log_successful_report_generation(final_report)
        return _build_reset_state_with_report(
            state, final_report, updated_session
        )

    except Exception as e:
        logger.error("❌ Investigation report generation failed: %s", e)
        error_report = f"Error generating investigation report. Details: {e}"
        # Update workflow session even in error case to preserve learning
        error_sessions = _update_workflow_session(state, error_report)
        return _build_reset_state_with_report(
            state, error_report, error_sessions
        )


def _build_report_context(state: GraphState) -> str:
    """
    Build comprehensive report context from all investigations in markdown format.

    Args:
        state: Current workflow state with investigations and assessment

    Returns:
        Markdown-formatted context string for the LLM
    """
    logger.debug(
        "📋 Building report context for %d investigations",
        len(state.investigations),
    )

    builder = MarkdownBuilder()
    builder.add_header("Network Investigation Report Context")

    # User Query Section
    builder.add_section("Original User Query")
    builder.add_text(state.user_query)

    # Investigation Overview
    builder.add_section("Investigation Overview")
    total_investigations = len(state.investigations)
    completed_investigations = [
        inv
        for inv in state.investigations
        if inv.status == InvestigationStatus.COMPLETED
    ]
    success_rate = (
        len(completed_investigations) / total_investigations
        if total_investigations > 0
        else 0.0
    )

    builder.add_bullet(f"Total devices investigated: {total_investigations}")
    builder.add_bullet(
        f"Successfully completed: {len(completed_investigations)}"
    )
    builder.add_bullet(f"Success rate: {success_rate:.1%}")
    builder.add_bullet(
        f"Retry attempts: {state.current_retries}/{state.max_retries}"
    )

    # Individual Investigation Results
    builder.add_section("Device Investigation Results")
    if not state.investigations:
        builder.add_text("No device investigations found.")
    else:
        for i, investigation in enumerate(state.investigations, 1):
            _add_investigation_details(builder, investigation, i)

    # Assessment Results
    builder.add_section("Assessment Results")
    if state.assessment:
        builder.add_bullet(
            f"Objective achieved: {state.assessment.is_objective_achieved}"
        )
        builder.add_text(
            f"**Assessment Notes:** {state.assessment.notes_for_final_report}"
        )
        if state.assessment.feedback_for_retry:
            builder.add_text(
                f"**Feedback for retry:** {state.assessment.feedback_for_retry}"
            )
    else:
        builder.add_text("No assessment results available.")

    # Historical Context from WorkflowSession
    sessions = (
        state.workflow_session if state.workflow_session is not None else []
    )
    _add_session_context(builder, sessions)

    context_string = builder.build()
    logger.debug(
        "📤 Report context prepared (%d characters)", len(context_string)
    )
    return context_string


def _add_investigation_details(
    builder: MarkdownBuilder, investigation: Investigation, index: int
) -> None:
    """
    Add individual investigation details to the markdown builder.

    Args:
        builder: Markdown builder instance
        investigation: Investigation object to format
        index: Investigation number for display
    """
    status_icon = {
        InvestigationStatus.COMPLETED: "✅",
        InvestigationStatus.FAILED: "❌",
        InvestigationStatus.IN_PROGRESS: "🔄",
        InvestigationStatus.PENDING: "⏳",
        InvestigationStatus.SKIPPED: "⏭️",
    }.get(investigation.status, "❓")

    builder.add_subsection(
        f"Investigation {index}: {investigation.device_name}"
    )
    builder.add_bullet(f"Status: {status_icon} {investigation.status.value}")
    builder.add_bullet(f"Device Profile: {investigation.device_profile}")
    builder.add_bullet(f"Role: {investigation.role}")
    builder.add_bullet(f"Priority: {investigation.priority}")

    if investigation.objective:
        builder.add_bullet(f"Objective: {investigation.objective}")

    if investigation.dependencies:
        builder.add_bullet(
            f"Dependencies: {', '.join(investigation.dependencies)}"
        )

    builder.add_bullet(
        f"Execution steps: {len(investigation.execution_results)}"
    )

    if investigation.error_details:
        builder.add_text(f"**Error Details:** {investigation.error_details}")

    if investigation.report:
        builder.add_text("**Investigation Report:**")
        builder.add_text(investigation.report)

    if investigation.working_plan_steps:
        builder.add_text("**Working Plan:**")
        builder.add_text(investigation.working_plan_steps)

    builder.add_empty_line()


def _add_session_context(
    builder: MarkdownBuilder, workflow_sessions: List[WorkflowSession]
) -> None:
    """
    Add workflow session context to the markdown builder.

    Args:
        builder: Markdown builder instance
        workflow_sessions: List of workflow sessions with historical data
    """
    builder.add_section("Historical Context")

    if not workflow_sessions:
        builder.add_text(
            "**No historical context available.** This is the first investigation session."
        )
        return

    # Show summary of all sessions
    builder.add_bullet(
        f"Total investigation sessions: {len(workflow_sessions)}"
    )

    # Show recent sessions (last 3)
    recent_sessions = workflow_sessions[-3:]
    builder.add_text(f"**Recent Sessions ({len(recent_sessions)}):**")

    for session in recent_sessions:
        builder.add_bullet(f"Session {session.session_id}:")

        # Previous Report from this session
        if session.previous_report:
            preview = (
                session.previous_report[:100] + "..."
                if len(session.previous_report) > 100
                else session.previous_report
            )
            builder.add_text(f"  - Report preview: {preview}")

        # Learned Patterns from this session
        if session.learned_patterns:
            builder.add_text(
                f"  - Learned patterns: {len(session.learned_patterns)} characters"
            )
            # Show preview of patterns
            patterns_preview = (
                session.learned_patterns[:200] + "..."
                if len(session.learned_patterns) > 200
                else session.learned_patterns
            )
            builder.add_text(f"    Preview: {patterns_preview}")

        # Device Relationships from this session
        if session.device_relationships:
            builder.add_text(
                f"  - Device relationships: {len(session.device_relationships)} characters"
            )
            # Show preview of relationships
            relationships_preview = (
                session.device_relationships[:200] + "..."
                if len(session.device_relationships) > 200
                else session.device_relationships
            )
            builder.add_text(f"    Preview: {relationships_preview}")

    builder.add_empty_line()


def _setup_report_model():
    """Setup and return the LLM model for report generation."""
    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)
    logger.debug(
        "🤖 Using model for report generation: %s", configuration.model
    )
    return model


def _generate_report(model, report_context: str) -> str:
    """
    Generate the final investigation report using the LLM.

    Args:
        model: LLM model for report generation
        report_context: Prepared report context

    Returns:
        Generated report string
    """
    logger.debug("🚀 Generating final report from LLM")

    messages = [
        SystemMessage(content=REPORT_GENERATOR_PROMPT),
        HumanMessage(content=report_context),
    ]

    response = model.invoke(messages)

    return _extract_report_content(response)


def _extract_report_content(response) -> str:
    """
    Extract content from LLM response, handling various response formats.

    Args:
        response: LLM response object

    Returns:
        Extracted content as string
    """
    if hasattr(response, "content"):
        content = response.content

        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            return " ".join(str(item) for item in content)
        else:
            return str(content)
    else:
        return str(response)


def _update_workflow_session(
    state: GraphState, final_report: str
) -> List[WorkflowSession]:
    """
    Create a new workflow session with LLM-generated learned patterns and findings from investigations.

    Args:
        state: Current GraphState with investigation results
        final_report: The generated final report to store in previous_reports

    Returns:
        Updated list of WorkflowSessions with new session appended
    """
    logger.debug(
        "📚 Creating new workflow session with investigation learnings"
    )

    import uuid

    # Create new session for this investigation
    session_id = str(uuid.uuid4())[:8]
    logger.info("🆕 Creating new workflow session: %s", session_id)

    # Generate learning insights using LLM
    learning_insights = _generate_learning_insights_with_llm(state)

    # Create new session with current report (single string, not list)
    new_session = WorkflowSession(
        session_id=session_id,
        previous_report=final_report if final_report else "",
        learned_patterns=learning_insights.learned_patterns,
        device_relationships=learning_insights.device_relationships,
    )

    # Append to existing sessions list (handle None case for backward compatibility)
    existing_sessions = (
        state.workflow_session if state.workflow_session is not None else []
    )
    updated_sessions = list(existing_sessions) + [new_session]

    # Keep only last 20 sessions to avoid unlimited growth
    updated_sessions = updated_sessions[-20:]

    logger.debug(
        "📈 Created new session with patterns (%d chars), relationships (%d chars), report (%d chars)",
        len(learning_insights.learned_patterns),
        len(learning_insights.device_relationships),
        len(final_report) if final_report else 0,
    )

    return updated_sessions


def _generate_learning_insights_with_llm(
    state: GraphState,
) -> LearningInsights:
    """
    Generate learning insights using LLM analysis of investigation results.

    Args:
        state: Current GraphState with investigation results

    Returns:
        LearningInsights object with learned patterns and device relationships
    """
    logger.debug("🧠 Generating learning insights using LLM analysis")

    try:
        # Build context for learning insights extraction
        insights_context = _build_learning_insights_context(state)

        # Setup model for learning insights generation
        model = _setup_report_model()

        # Use structured output for consistency with other nodes
        structured_model = model.with_structured_output(LearningInsights)

        messages = [
            SystemMessage(content=LEARNING_INSIGHTS_PROMPT),
            HumanMessage(content=insights_context),
        ]

        # Get structured response from LLM
        response = structured_model.invoke(messages)

        # Handle response based on type - sometimes structured_output returns dict
        if isinstance(response, dict):
            logger.debug(
                "🔄 Converting dict response to LearningInsights object using from_dict()"
            )
            learning_insights = LearningInsights.from_dict(response)
        elif isinstance(response, LearningInsights):
            logger.debug(
                "✅ Received properly structured LearningInsights object"
            )
            learning_insights = response
        else:
            logger.warning(
                "⚠️ Unexpected response type: %s", type(response).__name__
            )
            logger.debug("Response content: %s", str(response)[:200])
            # Try to extract and parse as JSON fallback
            raw_content = _extract_report_content(response)
            learning_insights = LearningInsights.from_json_string(raw_content)

        logger.info(
            "✅ Generated learning insights: patterns (%d chars), relationships (%d chars)",
            len(learning_insights.learned_patterns),
            len(learning_insights.device_relationships),
        )

        return learning_insights

    except Exception as e:
        logger.warning(
            "⚠️ Failed to generate learning insights with LLM: %s", e
        )
        logger.debug("Falling back to empty learning insights")

        # Log additional debug information for troubleshooting
        if "response" in locals():
            logger.debug("LLM response type: %s", type(response).__name__)
            logger.debug("LLM response object: %s", str(response)[:200])

            # If it's a dict, show the structure for debugging
            if isinstance(response, dict):
                logger.debug("Response keys: %s", list(response.keys()))
                if "learned_patterns" in response:
                    patterns_data = response.get("learned_patterns", {})
                    if isinstance(patterns_data, dict):
                        logger.debug(
                            "Learned patterns count: %d", len(patterns_data)
                        )
                    else:
                        logger.debug(
                            "Learned patterns length: %d chars",
                            len(str(patterns_data)),
                        )
                if "device_relationships" in response:
                    relationships_data = response.get(
                        "device_relationships", {}
                    )
                    if isinstance(relationships_data, dict):
                        logger.debug(
                            "Device relationships count: %d",
                            len(relationships_data),
                        )
                    else:
                        logger.debug(
                            "Device relationships length: %d chars",
                            len(str(relationships_data)),
                        )

        if "raw_content" in locals():
            logger.debug("Raw content type: %s", type(raw_content).__name__)
            logger.debug(
                "Raw content preview: %s",
                (
                    raw_content[:300] + "..."
                    if len(raw_content) > 300
                    else raw_content
                ),
            )

        # Return empty insights on failure using factory method
        return LearningInsights.empty()


def _build_learning_insights_context(state: GraphState) -> str:
    """
    Build context for learning insights extraction from investigation results.

    Args:
        state: Current GraphState with investigation results

    Returns:
        Formatted context string for LLM analysis
    """
    builder = MarkdownBuilder()
    builder.add_header("Investigation Data for Learning Insights Extraction")

    # Original user query
    builder.add_section("Original User Query")
    builder.add_text(state.user_query)

    # Investigation results summary
    builder.add_section("Investigation Results Summary")
    builder.add_bullet(f"Total investigations: {len(state.investigations)}")

    completed_count = len(
        [
            inv
            for inv in state.investigations
            if inv.status == InvestigationStatus.COMPLETED
        ]
    )
    builder.add_bullet(f"Completed investigations: {completed_count}")

    # Detailed investigation data
    builder.add_section("Detailed Investigation Data")

    for i, investigation in enumerate(state.investigations, 1):
        builder.add_subsection(
            f"Investigation {i}: {investigation.device_name}"
        )
        builder.add_bullet(f"Status: {investigation.status.value}")
        builder.add_bullet(f"Device Profile: {investigation.device_profile}")
        builder.add_bullet(f"Role: {investigation.role}")
        builder.add_bullet(f"Priority: {investigation.priority}")

        if investigation.objective:
            builder.add_bullet(f"Objective: {investigation.objective}")

        if investigation.dependencies:
            builder.add_bullet(
                f"Dependencies: {', '.join(investigation.dependencies)}"
            )

        builder.add_bullet(
            f"Execution Steps: {len(investigation.execution_results)}"
        )

        if investigation.error_details:
            builder.add_text(
                f"**Error Details:** {investigation.error_details}"
            )

        if investigation.report:
            builder.add_text("**Investigation Report:**")
            # Truncate very long reports for context
            report_preview = (
                investigation.report[:500] + "..."
                if len(investigation.report) > 500
                else investigation.report
            )
            builder.add_text(report_preview)

        builder.add_empty_line()

    # Assessment results if available
    if state.assessment:
        builder.add_section("Assessment Results")
        builder.add_bullet(
            f"Objective Achieved: {state.assessment.is_objective_achieved}"
        )
        if state.assessment.notes_for_final_report:
            builder.add_text(
                f"**Assessment Notes:** {state.assessment.notes_for_final_report}"
            )

    return builder.build()


def _log_successful_report_generation(report: str) -> None:
    """Log successful report generation details."""
    logger.info(
        "✅ Investigation report generation complete, length: %s characters",
        len(report),
    )
    logger.debug("📊 Generated report length: %s characters", len(report))


def _build_reset_state_with_report(
    state: GraphState,
    final_report: str,
    updated_sessions: List[WorkflowSession],
) -> GraphState:
    """
    Build a reset GraphState with only the final report and updated WorkflowSessions.

    This function implements the requirement to reset the GraphState to its initial state
    while preserving the WorkflowSession list with learned patterns and the final report.

    Args:
        state: Current GraphState (used only for user_query to create fresh state)
        final_report: Generated final report
        updated_sessions: Updated list of WorkflowSessions with new session appended

    Returns:
        Reset GraphState with final_report and workflow_session populated
    """
    logger.debug("🔄 Building reset state with final report")

    # Create a fresh GraphState with only essential information preserved
    reset_state = GraphState(
        user_query=state.user_query,  # Keep original query for reference
        final_report=final_report,
        workflow_session=updated_sessions,
    )

    logger.info(
        "✅ GraphState reset complete. Preserved: final_report (%d chars), %d workflow_sessions",
        len(final_report),
        len(updated_sessions),
    )

    return reset_state
