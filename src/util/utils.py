"""Utility functions for data serialization and message handling."""

import json
from typing import Any
from dataclasses import asdict

from langchain_core.messages import BaseMessage

# Add logging
from src.logging import get_logger

logger = get_logger(__name__)


def serialize_for_prompt(value: Any) -> str:
    """
    Utility function to serialize any value for use in prompts.

    This function handles dataclasses, regular dicts, lists, and other types
    by converting them to a JSON string representation that can be used in LLM prompts.

    Args:
        value: The value to serialize (can be dataclass, dict, list, etc.)

    Returns:
        A JSON string representation of the value
    """
    logger.debug("Serializing value of type %s for prompt", type(value))

    try:
        if hasattr(value, "__dataclass_fields__"):
            # It's a dataclass, convert to dict first
            result = json.dumps(asdict(value), indent=2, default=str)
        elif isinstance(value, (list, dict)):
            # Handle lists and dicts, including lists of dataclasses
            result = json.dumps(
                value,
                indent=2,
                default=lambda obj: (
                    asdict(obj)
                    if hasattr(obj, "__dataclass_fields__")
                    else str(obj)
                ),
            )
        else:
            # Handle strings and other basic types
            result = str(value)

        logger.debug(
            "Serialization complete, result length: %s characters", len(result)
        )
        return result

    except Exception as e:
        logger.error("Serialization failed: %s", e)
        return str(value)


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
