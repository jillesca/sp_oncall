"""LLM-related helpers (model initialization, etc.)."""

import os

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from pydantic import SecretStr

from src.logging import get_logger

logger = get_logger(__name__)

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def load_chat_model(fully_specified_name: str) -> BaseChatModel:
    """Load a chat model from a fully specified name like 'provider/model'."""
    logger.debug("Loading chat model: %s", fully_specified_name)

    try:
        provider, model = fully_specified_name.split("/", maxsplit=1)

        if provider == "openrouter":
            return _load_openrouter_model(model)

        chat_model = init_chat_model(model, model_provider=provider)
        logger.debug("Successfully loaded model: %s/%s", provider, model)
        return chat_model
    except Exception as e:
        logger.error(
            "Failed to load chat model %s: %s", fully_specified_name, e
        )
        raise


def _load_openrouter_model(model_name: str) -> BaseChatModel:
    """Load a model via OpenRouter using the OpenAI-compatible API."""
    from langchain_openai import ChatOpenAI

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY env var is required for OpenRouter models"
        )

    logger.debug("Loading OpenRouter model: %s", model_name)
    return ChatOpenAI(
        base_url=_OPENROUTER_BASE_URL,
        api_key=SecretStr(api_key),
        model=model_name,
    )
