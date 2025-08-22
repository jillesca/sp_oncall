"""
Common LLM utilities for all nodes.

This module provides shared functionality for LLM operations that are used
across different nodes to maintain consistency and reduce code duplication.
"""

from typing import List, Any
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langchain_core.language_models import BaseChatModel

from util.llm import load_chat_model
from configuration import Configuration
from src.logging import get_logger

logger = get_logger(__name__)


def load_model() -> BaseChatModel:
    """
    Load and return the configured LLM model.

    Returns:
        Configured LLM model for use in nodes
    """
    configuration = Configuration.from_context()
    model = load_chat_model(configuration.model)
    logger.debug("🤖 Using model: %s", configuration.model)
    return model


def create_messages(
    system_prompt: str,
    user_content: str,
    additional_messages: List[BaseMessage] = None,
) -> List[BaseMessage]:
    """
    Create a standard message list for LLM invocation.

    Args:
        system_prompt: System prompt for the LLM
        user_content: User content/context
        additional_messages: Optional additional messages to include

    Returns:
        List of messages ready for LLM invocation
    """
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    if additional_messages:
        messages.extend(additional_messages)

    return messages


def extract_response_content(response: Any) -> str:
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


def invoke_with_logging(
    model: BaseChatModel, messages: List[BaseMessage], operation_name: str
) -> Any:
    """
    Invoke LLM with consistent logging.

    Args:
        model: LLM model to invoke
        messages: Messages to send to the model
        operation_name: Name of the operation for logging

    Returns:
        LLM response
    """
    logger.debug("🚀 Invoking LLM for %s", operation_name)
    response = model.invoke(messages)
    logger.debug("📨 LLM %s response received", operation_name)
    return response
