"""Plan file helpers."""

import glob
import os
from typing import Dict, Optional


def load_plan_data(plans_dir: Optional[str] = None) -> Dict[str, str]:
    """Loads all plan files in the given directory as strings for prompting."""
    if plans_dir is None:
        # Default to the 'plans' directory at the project root
        plans_dir = os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "..", "plans"
            )
        )
    plans: Dict[str, str] = {}
    for plan_path in glob.glob(os.path.join(plans_dir, "*.json")):
        plan_filename = os.path.basename(plan_path)
        try:
            with open(plan_path, "r", encoding="utf-8") as f:
                plan_content = f.read()
            plans[plan_filename] = (
                f"--- plan: {plan_filename} ---\n{plan_content}\n--- end plan: {plan_filename} ---"
            )
        except Exception:
            continue
    return plans
