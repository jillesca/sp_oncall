"""
Response processing for input validation.

This module handles processing MCP responses to extract device names
and create Investigation objects.
"""

from typing import List
from dataclasses import dataclass

from langchain_core.messages import BaseMessage
from langchain_core.language_models import BaseChatModel

from schemas.state import Investigation
from src.util.validation import validate_structured_output, validate_investigation_planning
from src.logging import get_logger, debug_capture_object

logger = get_logger(__name__)


@dataclass
class InvestigationPlanningResponse:
    """Flat schema for device discovery output from the input validator.

    Using a list of strings rather than nested objects ensures compatibility
    across LLM providers that struggle with nested structured output schemas.
    """

    device_names: List[str]

    def __len__(self) -> int:
        return len(self.device_names)

    def __iter__(self):
        return iter(self.device_names)


def process_investigation_planning_response(
    response_content: BaseMessage, model: BaseChatModel
) -> InvestigationPlanningResponse:
    """
    Parses the MCP agent response content for device discovery.

    Args:
        response_content: Content from MCP agent response
        model: LLM model for structured output parsing

    Returns:
        InvestigationPlanningResponse with discovered device names
    """
    logger.debug("🧠 Getting structured output")

    result, violations = validate_structured_output(
        raw_text=response_content.content,
        schema=InvestigationPlanningResponse,
        model=model,
        validators=[validate_investigation_planning],
    )

    logger.debug("📋 Structured output captured: %s", result)
    debug_capture_object(result, label="_process_investigation_planning_response")

    if violations:
        logger.warning(
            "⚠️ Investigation planning validation violations: %s", violations
        )

    if isinstance(result, InvestigationPlanningResponse):
        return result
    elif isinstance(result, dict) and "device_names" in result:
        names = [n for n in result["device_names"] if n]
        return InvestigationPlanningResponse(device_names=names)

    logger.error("❌ Unexpected response format: %s", type(result))
    return InvestigationPlanningResponse(device_names=[])


def create_investigations_from_response(
    planning_response: InvestigationPlanningResponse,
) -> List[Investigation]:
    """
    Create Investigation objects from the device discovery response.

    Device profile and role start empty; they are enriched from the Store
    before execution and refined during per-device planning in the sub-graph.

    Args:
        planning_response: The parsed response containing discovered device names

    Returns:
        List of Investigation objects, one for each discovered device
    """
    logger.debug(
        "🏗️ Creating %d Investigation objects from planning response",
        len(planning_response),
    )

    investigations = []
    for device_name in planning_response:
        investigation = Investigation(device_name=device_name)
        investigations.append(investigation)
        logger.debug("  ✅ Created investigation for device: %s", device_name)

    return investigations
