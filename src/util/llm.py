"""LLM-related helpers (model initialization, etc.)."""

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

# Add logging
from src.logging import get_logger

logger = get_logger(__name__)


def load_chat_model(fully_specified_name: str) -> BaseChatModel:
    """Load a chat model from a fully specified name like 'provider/model'."""
    logger.debug("Loading chat model: %s", fully_specified_name)

    try:
        provider, model = fully_specified_name.split("/", maxsplit=1)
        chat_model = init_chat_model(model, model_provider=provider)
        logger.debug("Successfully loaded model: %s/%s", provider, model)
        return chat_model
    except Exception as e:
        logger.error(
            "Failed to load chat model %s: %s", fully_specified_name, e
        )
        raise
