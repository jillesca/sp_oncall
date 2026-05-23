"""Prompt loading with in-memory caching.

Prompts live in prompts/{name}.md at the project root.
They are read once and cached — prompts do not change at runtime.
"""

from pathlib import Path

from src.logging import get_logger
from src.util.file_loader import read_text_file

logger = get_logger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
_cache: dict[str, str] = {}


def load_prompt(name: str) -> str:
    """Return the Markdown content of prompts/{name}.md.

    Results are cached after the first read so repeated calls within a
    process incur no additional I/O.

    Args:
        name: Prompt file stem, e.g. "planner" loads prompts/planner.md.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    if name in _cache:
        return _cache[name]

    path = _PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    content = read_text_file(str(path))
    _cache[name] = content
    logger.debug("Loaded prompt: %s (%d characters)", name, len(content))
    return content
