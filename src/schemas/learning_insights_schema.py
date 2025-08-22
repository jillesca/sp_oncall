"""
Schema for learning insights extracted from network investigations.

This schema defines the structure for LLM-generated learning insights
that will be stored in HistoricalContext for future investigation context.
"""

import json
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class LearningInsights:
    """
    Learning insights extracted from network investigations by LLM analysis.

    This structure captures valuable patterns and relationships that can be
    used to inform future investigations. All fields contain human-readable
    markdown-formatted strings that other LLMs can easily understand and utilize.

    Attributes:
        learned_patterns: Key patterns discovered during investigations formatted as markdown.
        device_relationships: Network relationships and dependencies discovered formatted as markdown.
    """

    learned_patterns: str = field(default="")
    device_relationships: str = field(default="")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearningInsights":
        """
        Create LearningInsights from dictionary with validation and error handling.

        Args:
            data: Dictionary containing learned_patterns and device_relationships

        Returns:
            LearningInsights object with validated data

        Raises:
            ValueError: If data structure is invalid
        """
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data).__name__}")

        # Extract and validate learned_patterns
        learned_patterns_data = data.get("learned_patterns", {})
        if isinstance(learned_patterns_data, dict):
            # Convert dictionary to markdown string
            learned_patterns = cls._format_dict_as_markdown(
                learned_patterns_data, "Learned Patterns"
            )
        elif isinstance(learned_patterns_data, str):
            # Already a string, use as-is
            learned_patterns = learned_patterns_data
        else:
            raise ValueError(
                f"learned_patterns must be dict or str, got {type(learned_patterns_data).__name__}"
            )

        # Extract and validate device_relationships
        device_relationships_data = data.get("device_relationships", {})
        if isinstance(device_relationships_data, dict):
            # Convert dictionary to markdown string
            device_relationships = cls._format_dict_as_markdown(
                device_relationships_data, "Device Relationships"
            )
        elif isinstance(device_relationships_data, str):
            # Already a string, use as-is
            device_relationships = device_relationships_data
        else:
            raise ValueError(
                f"device_relationships must be dict or str, got {type(device_relationships_data).__name__}"
            )

        return cls(
            learned_patterns=learned_patterns,
            device_relationships=device_relationships,
        )

    @classmethod
    def from_json_string(cls, json_str: str) -> "LearningInsights":
        """
        Create LearningInsights from JSON string with error handling.

        Args:
            json_str: JSON string containing the insights data

        Returns:
            LearningInsights object

        Raises:
            ValueError: If JSON is invalid or data structure is wrong
        """
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string: {e}") from e

    @classmethod
    def empty(cls) -> "LearningInsights":
        """Create an empty LearningInsights object for fallback scenarios."""
        return cls(learned_patterns="", device_relationships="")

    @staticmethod
    def _format_dict_as_markdown(data: Dict[str, str], title: str) -> str:
        """
        Format a dictionary as markdown for better readability.

        Args:
            data: Dictionary to format
            title: Section title for the markdown

        Returns:
            Formatted markdown string
        """
        if not data:
            return ""

        lines = [f"## {title}", ""]
        for key, value in data.items():
            # Clean up the key to be more readable
            clean_key = key.replace("_", " ").title()
            lines.append(f"### {clean_key}")
            lines.append(value)
            lines.append("")  # Empty line for spacing

        return "\n".join(lines).strip()

    def __str__(self) -> str:
        """Return a human-readable representation of the learning insights."""
        result = []

        if self.learned_patterns:
            result.append(self.learned_patterns)

        if self.device_relationships:
            result.append(self.device_relationships)

        return (
            "\n\n".join(result)
            if result
            else "No learning insights available."
        )
