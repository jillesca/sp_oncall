"""Define the configurable parameters for the agent."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Annotated

from langchain_core.runnables import ensure_config
from langgraph.config import get_config

from src.logging import get_logger

logger = get_logger(__name__)

DEFAULT_MCP_CONFIG_FILENAME = "mcp_config.json"


class LLMModel(str, Enum):
    """Available LLM models for the agent. In the form: provider/model-name."""

    OPENAI_GPT5_NANO = "openai/gpt-5-nano"
    OPENAI_GPT5 = "openai/gpt-5"
    OPENAI_GPT5_MINI = "openai/gpt-5-mini"
    OPENAI_GPT5_4_NANO = "openai/gpt-5.4-nano"
    OPENROUTER_CLAUDE_SONNET_4 = "openrouter/anthropic/claude-sonnet-4"
    OPENROUTER_CLAUDE_SONNET_4_5 = "openrouter/anthropic/claude-sonnet-4-5"
    OPENROUTER_GEMINI_2_5_PRO = "openrouter/google/gemini-2.5-pro"

    def __str__(self) -> str:
        return self.value


@dataclass(kw_only=True)
class Configuration:
    """The configuration for the agent."""

    model: Annotated[LLMModel, {"__template_metadata__": {"kind": "llm"}}] = (
        field(
            default=LLMModel.OPENAI_GPT5_MINI,
            metadata={
                "description": "The language model to use for the agent's main interactions. "
                "Select from the available models in the LLMModel enum."
            },
        )
    )

    fast_model: str = field(
        default_factory=lambda: os.getenv(
            "SP_ONCALL_FAST_MODEL", "openai/gpt-4o-mini"
        ),
        metadata={
            "description": "The language model for structured output parsing. "
            "Faster and cheaper than the main model. "
            "Override with SP_ONCALL_FAST_MODEL env var."
        },
    )

    max_retries_per_device: int = field(
        default_factory=lambda: int(os.getenv("SP_ONCALL_MAX_RETRIES", "3")),
        metadata={
            "description": "Maximum number of execution retries per device investigation. "
            "Override with SP_ONCALL_MAX_RETRIES env var."
        },
    )

    mcp_client_config: dict = field(
        default_factory=dict,
        metadata={
            "description": "Configuration for the MCP client, including command and environment variables."
        },
    )

    @classmethod
    def from_context(cls) -> Configuration:
        """Create a Configuration instance from a RunnableConfig object."""
        logger.debug("Creating Configuration from context")

        try:
            config = get_config()
            logger.debug("Retrieved config from context")
        except RuntimeError:
            logger.debug("No config context available, using defaults")
            config = None

        config = ensure_config(config)
        configurable = config.get("configurable") or {}
        _fields = {f.name for f in fields(cls) if f.init}

        # Convert string model names to enum values if needed
        if "model" in configurable and isinstance(configurable["model"], str):
            try:
                # Try to find a matching enum by value
                for model_enum in LLMModel:
                    if model_enum.value == configurable["model"]:
                        configurable["model"] = model_enum
                        break
            except ValueError:
                # If no matching enum is found, use the default
                pass

        return cls(**{k: v for k, v in configurable.items() if k in _fields})
