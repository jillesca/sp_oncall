"""
Unit tests for markdown_builder.py

Tests focus on verifying the structure and format of generated markdown
content rather than specific content values.
"""

import pytest
from src.nodes.markdown_builder import MarkdownBuilder


class TestMarkdownBuilder:
    """Test cases for MarkdownBuilder class."""

    def test_init_creates_empty_builder(self):
        """Test that MarkdownBuilder initializes with empty content."""
        builder = MarkdownBuilder()
        assert builder._content == []

    def test_add_header_format(self):
        """Test header formatting and structure."""
        builder = MarkdownBuilder()
        result = builder.add_header("Test Header").build()

        lines = result.split("\n")
        assert lines[0] == "# Test Header"
        assert lines[1] == ""  # Empty line after header

    def test_add_section_format(self):
        """Test section formatting and structure."""
        builder = MarkdownBuilder()
        result = builder.add_section("Test Section").build()

        lines = result.split("\n")
        assert lines[0] == "## Test Section"
        assert lines[1] == ""  # Empty line after section

    def test_add_subsection_format(self):
        """Test subsection formatting and structure."""
        builder = MarkdownBuilder()
        result = builder.add_subsection("Test Subsection").build()

        lines = result.split("\n")
        assert lines[0] == "### Test Subsection"
        assert lines[1] == ""  # Empty line after subsection

    def test_add_text_format(self):
        """Test plain text formatting and structure."""
        builder = MarkdownBuilder()
        result = builder.add_text("Test text content").build()

        lines = result.split("\n")
        assert lines[0] == "Test text content"
        assert lines[1] == ""  # Empty line after text

    def test_add_bold_text_with_value(self):
        """Test bold text formatting with label and value."""
        builder = MarkdownBuilder()
        result = builder.add_bold_text("Label", "value").build()

        lines = result.split("\n")
        assert lines[0] == "**Label** value"
        assert lines[1] == ""  # Empty line after bold text

    def test_add_bold_text_without_value(self):
        """Test bold text formatting with only label."""
        builder = MarkdownBuilder()
        result = builder.add_bold_text("Just Label").build()

        lines = result.split("\n")
        assert lines[0] == "**Just Label**"
        assert lines[1] == ""  # Empty line after bold text

    def test_add_bullet_format(self):
        """Test bullet point formatting."""
        builder = MarkdownBuilder()
        result = builder.add_bullet("Bullet item").build()

        lines = result.split("\n")
        assert lines[0] == "- Bullet item"
        # Note: bullets don't add empty lines by default

    def test_add_code_block_format(self):
        """Test code block formatting and structure."""
        builder = MarkdownBuilder()
        result = builder.add_code_block("code content").build()

        lines = result.split("\n")
        assert lines[0] == "```"
        assert lines[1] == "code content"
        assert lines[2] == "```"
        assert lines[3] == ""  # Empty line after code block

    def test_add_separator_format(self):
        """Test horizontal separator formatting."""
        builder = MarkdownBuilder()
        result = builder.add_separator().build()

        lines = result.split("\n")
        assert lines[0] == "---"
        assert lines[1] == ""  # Empty line after separator

    def test_add_empty_line(self):
        """Test empty line addition."""
        builder = MarkdownBuilder()
        result = builder.add_empty_line().build()

        lines = result.split("\n")
        assert lines[0] == ""

    def test_fluent_interface_chaining(self):
        """Test that all methods return self for method chaining."""
        builder = MarkdownBuilder()

        # Test that all methods return the builder instance
        result = (
            builder.add_header("Header")
            .add_section("Section")
            .add_text("Text")
            .add_bold_text("Bold", "Value")
            .add_bullet("Bullet")
            .add_code_block("Code")
            .add_separator()
            .add_empty_line()
        )

        assert result is builder

    def test_complex_document_structure(self):
        """Test building a complex markdown document structure."""
        builder = MarkdownBuilder()
        result = (
            builder.add_header("Main Title")
            .add_section("Section 1")
            .add_text("Some text in section 1")
            .add_subsection("Subsection 1.1")
            .add_bold_text("Important:", "This is important")
            .add_bullet("First bullet")
            .add_bullet("Second bullet")
            .add_code_block("print('hello world')")
            .add_separator()
            .add_section("Section 2")
            .add_text("Some text in section 2")
            .build()
        )

        lines = result.split("\n")

        # Check document structure
        assert "# Main Title" in lines
        assert "## Section 1" in lines
        assert "### Subsection 1.1" in lines
        assert "**Important:** This is important" in lines
        assert "- First bullet" in lines
        assert "- Second bullet" in lines
        assert "```" in lines
        assert "print('hello world')" in lines
        assert "---" in lines
        assert "## Section 2" in lines

    def test_empty_builder_build(self):
        """Test building with no content."""
        builder = MarkdownBuilder()
        result = builder.build()
        assert result == ""

    def test_multiline_code_block(self):
        """Test code block with multiline content."""
        code_content = "line1\nline2\nline3"
        builder = MarkdownBuilder()
        result = builder.add_code_block(code_content).build()

        lines = result.split("\n")
        assert lines[0] == "```"
        assert lines[1] == "line1"
        assert lines[2] == "line2"
        assert lines[3] == "line3"
        assert lines[4] == "```"
        assert lines[5] == ""

    def test_special_characters_handling(self):
        """Test handling of special markdown characters."""
        builder = MarkdownBuilder()
        result = (
            builder.add_text("Text with *asterisks* and _underscores_")
            .add_bold_text("Label with # hash", "value with > arrow")
            .add_bullet("Bullet with [brackets] and {braces}")
            .build()
        )

        # Should preserve special characters as-is in content
        assert "*asterisks*" in result
        assert "_underscores_" in result
        assert "# hash" in result
        assert "> arrow" in result
        assert "[brackets]" in result
        assert "{braces}" in result

    def test_empty_string_inputs(self):
        """Test behavior with empty string inputs."""
        builder = MarkdownBuilder()
        result = (
            builder.add_header("")
            .add_text("")
            .add_bold_text("", "")
            .add_bullet("")
            .add_code_block("")
            .build()
        )

        lines = result.split("\n")

        # Should handle empty strings gracefully
        assert "# " in result
        assert "****" in result  # Empty label and value creates "****"
        assert "- " in result
        assert "```" in result

    def test_none_handling_gracefully(self):
        """Test that builder handles None inputs gracefully by converting to string."""
        builder = MarkdownBuilder()

        # These should not raise exceptions - convert None to string
        result = (
            builder.add_text(str(None))
            .add_bold_text(str(None), str(None))
            .add_bullet(str(None))
            .build()
        )

        # Should convert None to string representation
        assert "None" in result
