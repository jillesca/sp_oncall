import json
from typing import Dict, Any, List
from dataclasses import replace
from langchain_core.messages import SystemMessage

from schemas import GraphState
from schemas.state import Investigation, InvestigationStatus
from util.llm import load_chat_model
from util.utils import serialize_for_prompt
from configuration import Configuration
from prompts.report_generator import (
    REPORT_GENERATOR_PROMPT_TEMPLATE,
    MULTI_INVESTIGATION_REPORT_TEMPLATE,
)

# Add logging
from src.logging import get_logger, log_node_execution

logger = get_logger(__name__)


@log_node_execution("Multi-Investigation Reporter")
def multi_investigation_report_node(state: GraphState) -> GraphState:
    """
    Generate a comprehensive multi-device investigation report using an LLM.

    This function orchestrates the multi-investigation report generation by:
    1. Synthesizing findings from all completed investigations
    2. Incorporating assessor notes and historical context
    3. Updating workflow session with learned patterns
    4. Handling partial success scenarios
    5. Generating a comprehensive final report

    Args:
        state: The current GraphState with all investigation results

    Returns:
        Updated GraphState with final_report populated
    """
    logger.info("📄 Generating comprehensive multi-investigation report")

    try:
        report_input = _prepare_multi_investigation_report_input(state)
        model = _setup_report_generation_model()
        comprehensive_report = _generate_multi_investigation_report(
            model, report_input
        )

        # Update workflow session with learned patterns
        updated_state = _update_workflow_session_patterns(state, report_input)

        _log_successful_multi_report_generation(comprehensive_report)
        return _build_multi_report_state(updated_state, comprehensive_report)

    except Exception as e:
        logger.error("❌ Multi-investigation report generation failed: %s", e)
        error_report = f"Error generating comprehensive report. Details: {e}"
        return _build_multi_report_state(state, error_report)


@log_node_execution("Report Generator")
def generate_llm_report_node(state: GraphState) -> GraphState:
    """
    Generate a comprehensive summary report using an LLM.

    This function orchestrates the report generation workflow by:
    1. Preparing report input data from the current state
    2. Setting up the LLM model for report generation
    3. Generating the summary using the LLM
    4. Processing and validating the generated summary
    5. Updating the state with the final report

    Args:
        state: The current GraphState containing all necessary information.

    Returns:
        An updated GraphState with the 'summary' field populated by the LLM.
    """
    logger.info("📄 Generating final summary report")

    try:
        prompt_input = _prepare_report_input(state)
        model = _setup_report_generation_model()
        llm_summary = _generate_llm_summary(model, prompt_input)

        _log_successful_report_generation(llm_summary)
        return _build_report_state(state, llm_summary)

    except Exception as e:
        logger.error("❌ Report generation failed: %s", e)
        error_summary = f"Error generating LLM summary. Details: {e}"
        return _build_report_state(state, error_summary)


def _prepare_report_input(state: GraphState) -> Dict[str, str]:
    """
    Extract and prepare data from the state for the report generator.

    Args:
        state: The current graph state

    Returns:
        Dictionary with formatted input for the prompt template
    """
    logger.debug("📋 Preparing report input data")

    context = {
        "user_query": state.user_query or "N/A",
        "device_name": state.device_name or "N/A",
        "objective": state.objective or "N/A",
        "working_plan_steps": serialize_for_prompt(state.working_plan_steps),
        "execution_results": serialize_for_prompt(state.execution_results),
        "assessor_notes_for_final_report": state.assessor_notes_for_final_report
        or "None",
    }

    logger.debug(
        "📤 Report input prepared for device: %s", context["device_name"]
    )
    return context


def _setup_report_generation_model():
    """Setup and return the LLM model for report generation."""
    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)
    logger.debug(
        "🤖 Using model for report generation: %s", configuration.model
    )
    return model


def _generate_llm_summary(model, prompt_input: Dict[str, str]) -> str:
    """
    Generate a summary using the LLM based on provided input.

    Args:
        model: LLM model for report generation
        prompt_input: Dictionary with formatted data for the prompt

    Returns:
        Generated summary string

    Raises:
        Exception: If report generation fails
    """
    logger.debug("🚀 Generating report from LLM")

    system_message = REPORT_GENERATOR_PROMPT_TEMPLATE.format(**prompt_input)
    response = model.invoke([SystemMessage(content=system_message)])

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


def _log_successful_report_generation(summary: str) -> None:
    """Log successful report generation details."""
    logger.info(
        "✅ Report generation complete, length: %s characters", len(summary)
    )
    logger.debug("📊 Generated report length: %s characters", len(summary))


def _build_report_state(state: GraphState, summary: str) -> GraphState:
    """
    Build the final state with the generated report.

    Args:
        state: Current GraphState
        summary: Generated summary report

    Returns:
        Updated GraphState with summary
    """
    logger.debug("🏗️ Building final report state")

    return replace(state, summary=summary)


def _prepare_multi_investigation_report_input(
    state: GraphState,
) -> Dict[str, str]:
    """
    Extract and prepare data from multi-investigation state for the report generator.

    Args:
        state: The current graph state with investigations

    Returns:
        Dictionary with formatted input for the multi-investigation report template
    """
    logger.debug("📋 Preparing multi-investigation report input data")

    # Calculate investigation statistics
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

    # Prepare investigation summaries
    investigation_summaries = _format_investigation_summaries(
        state.investigations
    )

    # Prepare cross-device analysis
    cross_device_analysis = _prepare_cross_device_analysis(
        completed_investigations
    )

    # Prepare session context
    session_context = _format_session_context(state.workflow_session)

    context = {
        "user_query": state.user_query or "N/A",
        "investigation_scope": "Multi-device network investigation",
        "total_investigations": str(total_investigations),
        "success_rate": f"{success_rate:.1%}",
        "investigation_summaries": investigation_summaries,
        "cross_device_analysis": cross_device_analysis,
        "assessor_notes": state.assessor_notes_for_final_report or "None",
        "session_context": session_context,
    }

    logger.debug(
        "📤 Multi-investigation report input prepared for %d devices",
        total_investigations,
    )
    return context


def _format_investigation_summaries(
    investigations: List[Investigation],
) -> str:
    """Format individual investigation summaries for the report."""
    summaries = []

    for investigation in investigations:
        status_icon = (
            "✅"
            if investigation.status == InvestigationStatus.COMPLETED
            else "❌"
        )
        summary = f"{status_icon} **{investigation.device_name}** ({investigation.device_profile})\n"
        summary += f"   - Status: {investigation.status.value}\n"
        summary += f"   - Objective: {investigation.objective or 'N/A'}\n"
        summary += f"   - Results: {len(investigation.execution_results)} execution steps\n"

        if investigation.error_details:
            summary += f"   - Error: {investigation.error_details}\n"

        if investigation.report:
            # Truncate report if too long
            report_preview = (
                investigation.report[:200] + "..."
                if len(investigation.report) > 200
                else investigation.report
            )
            summary += f"   - Findings: {report_preview}\n"

        summaries.append(summary)

    return "\n".join(summaries)


def _prepare_cross_device_analysis(
    completed_investigations: List[Investigation],
) -> str:
    """Prepare cross-device analysis for completed investigations."""
    if len(completed_investigations) < 2:
        return (
            "Insufficient completed investigations for cross-device analysis."
        )

    # Simple pattern analysis
    device_profiles = [inv.device_profile for inv in completed_investigations]
    profile_counts = {}
    for profile in device_profiles:
        profile_counts[profile] = profile_counts.get(profile, 0) + 1

    analysis = f"Investigated {len(completed_investigations)} devices across {len(profile_counts)} device types:\n"
    for profile, count in profile_counts.items():
        analysis += f"- {profile}: {count} device(s)\n"

    return analysis


def _format_session_context(workflow_session) -> str:
    """Format workflow session context for the report."""
    if not workflow_session:
        return "No session context available."

    context = f"Session ID: {workflow_session.session_id}\n"
    context += (
        f"Historical Reports: {len(workflow_session.previous_reports)}\n"
    )
    context += f"Learned Patterns: {len(workflow_session.learned_patterns)}\n"
    context += (
        f"Device Relationships: {len(workflow_session.device_relationships)}"
    )

    return context


def _generate_multi_investigation_report(
    model, report_input: Dict[str, str]
) -> str:
    """
    Generate a comprehensive multi-investigation report using the LLM.

    Args:
        model: LLM model for report generation
        report_input: Dictionary with formatted data for the prompt

    Returns:
        Generated comprehensive report string
    """
    logger.debug(
        "🚀 Generating comprehensive multi-investigation report from LLM"
    )

    system_message = MULTI_INVESTIGATION_REPORT_TEMPLATE.format(**report_input)
    response = model.invoke([SystemMessage(content=system_message)])

    return _extract_report_content(response)


def _update_workflow_session_patterns(
    state: GraphState, report_input: Dict[str, str]
) -> GraphState:
    """
    Update workflow session with learned patterns from this investigation.

    Args:
        state: Current GraphState
        report_input: Report input data containing investigation insights

    Returns:
        Updated GraphState with enhanced workflow session
    """
    if not state.workflow_session:
        return state

    # Extract patterns from successful investigations
    patterns = {}
    for investigation in state.investigations:
        if investigation.status == InvestigationStatus.COMPLETED:
            pattern_key = f"{investigation.device_profile}_investigation"
            patterns[pattern_key] = {
                "device_profile": investigation.device_profile,
                "steps_count": len(investigation.working_plan_steps),
                "success": True,
                "timestamp": "current",  # In real implementation, use actual timestamp
            }

    # Update session with new patterns
    updated_session = replace(
        state.workflow_session,
        learned_patterns={
            **state.workflow_session.learned_patterns,
            **patterns,
        },
    )

    return replace(state, workflow_session=updated_session)


def _log_successful_multi_report_generation(report: str) -> None:
    """Log successful multi-investigation report generation details."""
    logger.info(
        "✅ Multi-investigation report generation complete, length: %s characters",
        len(report),
    )
    logger.debug(
        "📊 Generated comprehensive report length: %s characters", len(report)
    )


def _build_multi_report_state(
    state: GraphState, comprehensive_report: str
) -> GraphState:
    """
    Build the final state with the generated multi-investigation report.

    Args:
        state: Current GraphState
        comprehensive_report: Generated comprehensive report

    Returns:
        Updated GraphState with final_report
    """
    logger.debug("🏗️ Building final multi-investigation report state")

    return replace(state, final_report=comprehensive_report)
