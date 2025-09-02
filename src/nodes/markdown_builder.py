"""
Markdown building utilities for nodes.

This module provides a clean, readable interface for building markdown content
without the need for complex list manipulations. It follows the DRY principle
by centralizing markdown generation logic that can be reused across different nodes.
"""


class MarkdownBuilder:
    """
    A simple, readable markdown builder that replaces complex list.extend() patterns.

    This class provides a clean, fluent interface for building markdown content
    without the need for complex list manipulations.
    """

    def __init__(self):
        self._content = []

    def add_header(self, text: str) -> "MarkdownBuilder":
        """Add a top-level header."""
        self._content.append(f"# {text}")
        self._content.append("")
        return self

    def add_section(self, text: str) -> "MarkdownBuilder":
        """Add a section header."""
        self._content.append(f"## {text}")
        self._content.append("")
        return self

    def add_subsection(self, text: str) -> "MarkdownBuilder":
        """Add a subsection header."""
        self._content.append(f"### {text}")
        self._content.append("")
        return self

    def add_text(self, text: str) -> "MarkdownBuilder":
        """Add plain text."""
        self._content.append(text)
        self._content.append("")
        return self

    def add_bold_text(self, label: str, value: str = "") -> "MarkdownBuilder":
        """Add bold text with optional value."""
        if value:
            self._content.append(f"**{label}** {value}")
        else:
            self._content.append(f"**{label}**")
        self._content.append("")
        return self

    def add_bullet(self, text: str) -> "MarkdownBuilder":
        """Add a bullet point."""
        self._content.append(f"- {text}")
        return self

    def add_code_block(self, content: str) -> "MarkdownBuilder":
        """Add a code block."""
        self._content.append("```")
        self._content.append(content)
        self._content.append("```")
        self._content.append("")
        return self

    def add_separator(self) -> "MarkdownBuilder":
        """Add a horizontal separator."""
        self._content.append("---")
        self._content.append("")
        return self

    def add_empty_line(self) -> "MarkdownBuilder":
        """Add an empty line."""
        self._content.append("")
        return self

    def build(self) -> str:
        """Build the final markdown string."""
        return "\n".join(self._content)
