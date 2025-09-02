"""Plan file helpers."""

import os
from typing import Any, Dict, List, Optional

from src.logging import get_logger
from src.util.file_loader import load_json_files_from_directory

logger = get_logger(__name__)


def load_plans(plans_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load all plan files from the given directory as a list of dictionaries.

    Args:
        plans_dir: Directory containing plan JSON files. If None, defaults to
                  the 'plans' directory at the project root.

    Returns:
        List of dictionaries, each representing a plan with structure:
        {
            "intent": str,
            "description": str,
            "steps": List[str]
        }
    """
    plans_directory = _get_plans_directory(plans_dir)
    logger.debug("Loading plans from directory: %s", plans_directory)

    try:
        plans = load_json_files_from_directory(plans_directory)
        logger.info("Successfully loaded %s plans", len(plans))
        return plans
    except Exception as e:
        logger.error(
            "Failed to load plans from directory %s: %s", plans_directory, e
        )
        return []


def plans_to_string(
    plans: List[Dict[str, Any]], format_style: str = "markdown"
) -> str:
    """Convert a list of plan dictionaries to a formatted string for LLM consumption.

    Args:
        plans: List of plan dictionaries
        format_style: Format style - "markdown", "structured", or "simple"

    Returns:
        Formatted string containing all plans with clear separators optimized for LLM parsing
    """
    if not plans:
        logger.warning("No plans provided to convert to string")
        return "No plans available."

    logger.debug(
        "Converting %s plans to string format using %s style",
        len(plans),
        format_style,
    )

    if format_style == "markdown":
        return _format_plans_markdown(plans)
    elif format_style == "structured":
        return _format_plans_structured(plans)
    else:  # simple
        return _format_plans_simple(plans)


def _format_plans_markdown(plans: List[Dict[str, Any]]) -> str:
    """Format plans using markdown-style headers for optimal LLM parsing."""
    formatted_plans = []
    for i, plan in enumerate(plans, 1):
        intent = plan.get("intent", "unknown")
        description = plan.get("description", "No description available")
        steps = plan.get("steps", [])

        # Use markdown-like formatting for better LLM parsing
        plan_text = f"## Plan {i}: {intent}\n\n"
        plan_text += f"**Description:** {description}\n\n"
        plan_text += "**Steps:**\n"

        for step_num, step in enumerate(steps, 1):
            plan_text += f"{step_num}. {step}\n"

        formatted_plans.append(plan_text.rstrip())

    # Use clear section separators
    separator = "\n\n" + "-" * 80 + "\n\n"
    result = separator.join(formatted_plans) + "\n"
    logger.debug(
        "Successfully converted plans to string format using markdown style"
    )
    return result


def _format_plans_structured(plans: List[Dict[str, Any]]) -> str:
    """Format plans using clear structured format with consistent indentation."""
    formatted_plans = []
    for i, plan in enumerate(plans, 1):
        intent = plan.get("intent", "unknown")
        description = plan.get("description", "No description available")
        steps = plan.get("steps", [])

        plan_text = f"PLAN {i}: {intent.upper()}\n"
        plan_text += f"  Description: {description}\n"
        plan_text += f"  Steps:\n"

        for step_num, step in enumerate(steps, 1):
            plan_text += f"    {step_num}. {step}\n"

        formatted_plans.append(plan_text.rstrip())

    # Use clear section separators
    separator = "\n\n" + "=" * 60 + "\n\n"
    result = separator.join(formatted_plans) + "\n"
    return result


def _format_plans_simple(plans: List[Dict[str, Any]]) -> str:
    """Format plans using simple, clean format (original improved version)."""
    formatted_plans = []
    for plan in plans:
        intent = plan.get("intent", "unknown")
        description = plan.get("description", "No description available")
        steps = plan.get("steps", [])

        plan_text = f"Plan: {intent}\n"
        plan_text += f"Description: {description}\n"
        plan_text += "Steps:\n"

        for step_num, step in enumerate(steps, 1):
            plan_text += f"  {step_num}. {step}\n"

        formatted_plans.append(plan_text.rstrip())

    # Use clear separators
    separator = "\n\n" + "=" * 40 + "\n\n"
    result = separator.join(formatted_plans) + "\n"
    return result


def _get_plans_directory(plans_dir: Optional[str]) -> str:
    """Get the plans directory path, using default if not provided."""
    if plans_dir is not None:
        return plans_dir

    # Default to the 'plans' directory at the project root
    return os.path.abspath(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "plans")
    )
