"""Workflow session management for reporter."""

import uuid
from typing import List

from langchain_core.messages import SystemMessage, HumanMessage

from schemas import GraphState, LearningInsights
from schemas.state import WorkflowSession, InvestigationStatus
from nodes.markdown_builder import MarkdownBuilder
from prompts.learning_insights import LEARNING_INSIGHTS_PROMPT
from src.logging import get_logger

logger = get_logger(__name__)


def update_workflow_session(
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
        from nodes.common import load_model

        # Build context for learning insights extraction
        insights_context = _build_learning_insights_context(state)

        # Setup model for learning insights generation
        model = load_model()

        # Use structured output for consistency with other nodes
        structured_model = model.with_structured_output(LearningInsights)

        messages = [
            SystemMessage(content=LEARNING_INSIGHTS_PROMPT),
            HumanMessage(content=insights_context),
        ]

        # Get structured response from LLM
        response = structured_model.invoke(messages)

        # Handle response based on type
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
            # Try to extract and parse as JSON fallback
            from .generation import _extract_report_content

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
