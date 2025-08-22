"""
Common response processing utilities for all nodes.

This module provides shared functionality for processing LLM responses
and handling structured output across different nodes.
"""

from typing import Any, Type, TypeVar
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

from src.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def process_structured_response(
    model: BaseChatModel,
    messages: BaseMessage | str,
    schema: Type[T],
    operation_name: str,
) -> T:
    """
    Process LLM response with structured output.

    Args:
        model: LLM model to use
        messages: Messages to send or content string
        schema: Pydantic schema class for structured output
        operation_name: Name of operation for logging

    Returns:
        Structured response object of type T
    """
    logger.debug("🧠 Getting structured output for %s", operation_name)

    try:
        # Handle both message objects and string content
        if isinstance(messages, str):
            content = messages
        else:
            content = (
                messages.content
                if hasattr(messages, "content")
                else str(messages)
            )

        structured_model = model.with_structured_output(schema=schema)
        response = structured_model.invoke(input=content)

        logger.debug(
            "📋 Structured output captured for %s: %s",
            operation_name,
            response,
        )

        return ensure_proper_format(response, schema)

    except Exception as e:
        logger.error(
            "❌ Structured output processing failed for %s: %s",
            operation_name,
            e,
        )
        raise


def ensure_proper_format(response: Any, schema: Type[T]) -> T:
    """
    Ensure response is in the proper format for the given schema.

    Args:
        response: Raw response from LLM
        schema: Expected schema class

    Returns:
        Properly formatted response object
    """
    if isinstance(response, schema):
        return response

    if isinstance(response, dict):
        try:
            # Try to create instance from dict
            return schema(**response)
        except Exception as e:
            logger.warning(
                "⚠️ Failed to create %s from dict: %s", schema.__name__, e
            )
            # Return a default instance if schema supports it
            if hasattr(schema, "empty") and callable(getattr(schema, "empty")):
                return schema.empty()
            raise

    # If we can't convert, raise an error
    raise ValueError(
        f"Cannot convert response of type {type(response)} to {schema.__name__}"
    )


def handle_response_errors(
    error: Exception, operation_name: str, default_value: Any = None
) -> Any:
    """
    Handle errors in response processing with consistent logging.

    Args:
        error: Exception that occurred
        operation_name: Name of operation for logging
        default_value: Default value to return on error

    Returns:
        Default value or raises exception
    """
    logger.error(
        "❌ Response processing failed for %s: %s", operation_name, error
    )

    if default_value is not None:
        logger.debug("🔄 Returning default value for %s", operation_name)
        return default_value

    raise error
