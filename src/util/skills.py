"""Skill file helpers."""

from pathlib import Path
from typing import List, Optional

from src.logging import get_logger
from src.util.file_loader import read_text_file

logger = get_logger(__name__)

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills"

_SEPARATOR = "\n\n" + "-" * 80 + "\n\n"


def load_skills(
    skill_names: Optional[List[str]] = None,
    skills_dir: Optional[str] = None,
) -> str:
    """Load skill Markdown files and return them as a single formatted string.

    Args:
        skill_names: If provided, only load skills with these names (file stem).
                     If None, load all skills in the directory.
        skills_dir: Override the default skills directory path.

    Returns:
        Concatenated Markdown content of all matching skills, or a fallback
        message when no skills are found.
    """
    directory = Path(skills_dir) if skills_dir else SKILLS_DIR

    if not directory.is_dir():
        logger.warning("Skills directory does not exist: %s", directory)
        return "No skills available."

    paths = _resolve_skill_paths(directory, skill_names)

    if not paths:
        logger.warning("No skill files found in %s", directory)
        return "No skills available."

    return _load_and_join(paths)


def _resolve_skill_paths(
    directory: Path, skill_names: Optional[List[str]]
) -> List[Path]:
    """Return skill file paths for the given names, or all .md files if names is None."""
    if skill_names is not None:
        paths = [directory / f"{name}.md" for name in skill_names]
        return [p for p in paths if p.exists()]
    return sorted(directory.glob("*.md"))


def _load_and_join(paths: List[Path]) -> str:
    """Read each skill file and join them with a separator."""
    contents = []
    for path in paths:
        try:
            contents.append(read_text_file(str(path)))
            logger.debug("Loaded skill: %s", path.stem)
        except Exception as e:
            logger.warning("Failed to load skill %s: %s", path.stem, e)

    logger.debug("Loaded %d skills", len(contents))
    return _SEPARATOR.join(contents)
