"""Define the configurable parameters for the agent."""

from __future__ import annotations
from dataclasses import dataclass, field, fields
from typing import Annotated
from enum import Enum

from langchain_core.runnables import ensure_config
from langgraph.config import get_config

from sp_oncall import prompts


class LLMModel(str, Enum):
    """Available LLM models for the agent. In the form: provider/model-name."""

    OLLAMA_QWEN3_8B = "ollama/qwen3:8b"
    OLLAMA_LLAMA3_1 = "ollama/llama3.1"
    OPENAI_GPT4O_MINI = "openai/gpt-4o-mini"
    OPENAI_GPT4 = "openai/gpt-4"

    def __str__(self) -> str:
        """Return the string value of the enum."""
        return self.value


@dataclass(kw_only=True)
class Configuration:
    """The configuration for the agent."""

    model: Annotated[LLMModel, {"__template_metadata__": {"kind": "llm"}}] = (
        field(
            default=LLMModel.OPENAI_GPT4O_MINI,
            metadata={
                "description": "The language model to use for the agent's main interactions. "
                "Select from the available models in the LLMModel enum."
            },
        )
    )

    max_search_results: int = field(
        default=10,
        metadata={
            "description": "The maximum number of search results to return for each search query."
        },
    )

    @classmethod
    def from_context(cls) -> Configuration:
        """Create a Configuration instance from a RunnableConfig object."""
        try:
            config = get_config()
        except RuntimeError:
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
