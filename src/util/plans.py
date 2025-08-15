"""Plan file helpers."""

import glob
import os
from typing import Dict, Optional

# Add logging
from src.logging import get_logger

logger = get_logger(__name__)


def load_plan_data(plans_dir: Optional[str] = None) -> Dict[str, str]:
    """Loads all plan files in the given directory as strings for prompting."""
    if plans_dir is None:
        # Default to the 'plans' directory at the project root
        plans_dir = os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "..", "plans"
            )
        )

    logger.debug(f"Loading plan files from directory: {plans_dir}")

    plans: Dict[str, str] = {}
    plan_files = glob.glob(os.path.join(plans_dir, "*.json"))
    logger.debug(f"Found {len(plan_files)} plan files")

    for plan_path in plan_files:
        plan_filename = os.path.basename(plan_path)
        try:
            with open(plan_path, "r", encoding="utf-8") as f:
                plan_content = f.read()
            plans[plan_filename] = (
                f"--- plan: {plan_filename} ---\n{plan_content}\n--- end plan: {plan_filename} ---"
            )
            logger.debug(f"Loaded plan: {plan_filename}")
        except Exception as e:
            logger.warning(f"Failed to load plan {plan_filename}: {e}")
            continue

    logger.info(f"Successfully loaded {len(plans)} plan files")
    return plans
