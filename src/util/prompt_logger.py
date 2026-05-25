"""Prompt logging for LLM calls.

Writes the final assembled prompt (system + human message) to a per-run log
directory so every LLM call can be reviewed and the instructions improved.

Call start_run() once at the beginning of each graph run. Every subsequent
log_prompt() call writes a separate file into that run's directory.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.logging import get_logger

logger = get_logger(__name__)

_LOGS_ROOT = Path("logs")


@dataclass
class _RunState:
    current_dir: Optional[Path] = field(default=None)


_state = _RunState()


def start_run() -> None:
    """Initialize a new run log directory.

    Creates a timestamped subdirectory under logs/. Call this exactly once
    at the start of each graph run (e.g., from input_validator_node).
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    _state.current_dir = _LOGS_ROOT / timestamp
    _state.current_dir.mkdir(parents=True, exist_ok=True)
    logger.info("📝 Prompt logging initialized at: %s", _state.current_dir)


def log_prompt(
    node_name: str,
    system_prompt: str,
    human_message: str,
    device_name: Optional[str] = None,
    attempt: int = 1,
) -> None:
    """Log the assembled prompt sent to an LLM call.

    Writes one file per call. File is named by node, device (if applicable),
    and attempt number so multiple retries produce distinct, inspectable files.

    Args:
        node_name: Name of the graph node or agent making the LLM call.
        system_prompt: System prompt content.
        human_message: Human message content (already assembled, may span sections).
        device_name: Device being investigated, when applicable.
        attempt: Retry attempt number (1-based).
    """
    if _state.current_dir is None:
        logger.warning(
            "⚠️ Prompt logger not initialized — start_run() was not called before log_prompt()"
        )
        return

    filepath = _state.current_dir / _build_filename(node_name, device_name, attempt)
    filepath.write_text(
        _format_log(node_name, device_name, attempt, system_prompt, human_message),
        encoding="utf-8",
    )
    logger.debug("📝 Prompt logged: %s", filepath)


def _build_filename(
    node_name: str, device_name: Optional[str], attempt: int
) -> str:
    parts = [node_name]
    if device_name:
        parts.append(device_name)
    parts.append(f"attempt-{attempt}")
    return "_".join(parts) + ".md"


def _format_log(
    node_name: str,
    device_name: Optional[str],
    attempt: int,
    system_prompt: str,
    human_message: str,
) -> str:
    title = node_name
    if device_name:
        title += f" — {device_name}"

    return "\n\n".join(
        [
            f"# {title} (attempt {attempt})",
            "## System Prompt",
            system_prompt,
            "## Human Message",
            human_message,
        ]
    )
