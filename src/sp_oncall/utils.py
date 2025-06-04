"""Utility & helper functions."""

import os
import glob
from typing import Dict, Optional

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage


def get_message_text(msg: BaseMessage) -> str:
    """Get the text content of a message."""
    content = msg.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    else:
        txts = [
            c if isinstance(c, str) else (c.get("text") or "") for c in content
        ]
        return "".join(txts).strip()


def load_chat_model(fully_specified_name: str) -> BaseChatModel:
    """Load a chat model from a fully specified name.

    Args:
        fully_specified_name (str): String in the format 'provider/model'.
    """
    provider, model = fully_specified_name.split("/", maxsplit=1)
    return init_chat_model(model, model_provider=provider)


def load_plan_data(plans_dir: Optional[str] = None) -> Dict[str, str]:
    """Loads all plan files in the given directory as strings.

    Args:
        plans_dir: The directory containing plan files. Defaults to '../plans' relative to this file.

    Returns:
        Dict mapping plan filenames to their string content.
    """
    if plans_dir is None:
        # Default to the 'plans' directory at the project root
        plans_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "..", "plans"
        )
        plans_dir = os.path.abspath(plans_dir)
    plans = {}
    for plan_path in glob.glob(os.path.join(plans_dir, "*.json")):
        plan_filename = os.path.basename(plan_path)
        try:
            with open(plan_path, "r") as f:
                plan_content = f.read()
            # Optionally, add delimiters for LLM clarity
            plans[plan_filename] = (
                f"--- plan: {plan_filename} ---\n{plan_content}\n--- end plan: {plan_filename} ---"
            )
        except Exception as e:
            # Skip files that can't be read
            continue
    return plans
