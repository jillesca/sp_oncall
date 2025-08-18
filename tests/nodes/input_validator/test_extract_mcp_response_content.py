"""
Tests for _extract_mcp_response_content function.
"""

import pytest
import sys
import os
from langchain_core.messages import AIMessage, ToolMessage

# Add the src directory to the path to avoid circular import issues
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src")
)

# Import the function under test
from nodes.input_validator import _extract_mcp_response_content

# Import test data
from .mpc_response_data import mpc_response


class TestExtractMcpResponseContent:
    """Test suite for _extract_mcp_response_content function."""

    def test_extract_content_from_valid_mcp_response(self):
        """Test extracting content from a valid MCP response with the test data."""
        # Act
        result = _extract_mcp_response_content(mpc_response)

        # Assert
        expected_content = '{\n  "device_name": "xrd-1"\n}'
        assert result == expected_content

    def test_extract_content_missing_messages_key(self):
        """Test error handling when 'messages' key is missing."""
        # Arrange
        invalid_response = {"some_other_key": "value"}

        # Act & Assert
        with pytest.raises(
            ValueError,
            match="Invalid MCP response format: missing 'messages' key",
        ):
            _extract_mcp_response_content(invalid_response)

    def test_extract_content_empty_messages_list(self):
        """Test error handling when messages list is empty."""
        # Arrange
        invalid_response = {"messages": []}

        # Act & Assert
        with pytest.raises(
            ValueError,
            match="Invalid MCP response format: 'messages' is not a list or is empty",
        ):
            _extract_mcp_response_content(invalid_response)

    def test_extract_content_messages_not_list(self):
        """Test error handling when messages is not a list."""
        # Arrange
        invalid_response = {"messages": "not a list"}

        # Act & Assert
        with pytest.raises(
            ValueError,
            match="Invalid MCP response format: 'messages' is not a list or is empty",
        ):
            _extract_mcp_response_content(invalid_response)

    def test_extract_content_no_ai_message(self):
        """Test error handling when no AIMessage is found in messages."""
        # Arrange
        response_without_ai_message = {
            "messages": [
                ToolMessage(
                    content="Some tool content",
                    name="some_tool",
                    id="tool-id",
                    tool_call_id="call-id",
                )
            ]
        }

        # Act & Assert
        with pytest.raises(
            ValueError, match="No AIMessage found in MCP response messages"
        ):
            _extract_mcp_response_content(response_without_ai_message)

    def test_extract_content_multiple_ai_messages_gets_last(self):
        """Test that the function returns content from the last AIMessage."""
        # Arrange
        response_with_multiple_ai_messages = {
            "messages": [
                AIMessage(content="First AI message", id="first-ai"),
                ToolMessage(
                    content="Tool message",
                    name="tool",
                    id="tool-id",
                    tool_call_id="call-id",
                ),
                AIMessage(content="Second AI message", id="second-ai"),
                AIMessage(content="Last AI message", id="last-ai"),
            ]
        }

        # Act
        result = _extract_mcp_response_content(
            response_with_multiple_ai_messages
        )

        # Assert
        assert result == "Last AI message"

    def test_extract_content_with_empty_ai_message_content(self):
        """Test extraction when AIMessage has empty content."""
        # Arrange
        response_with_empty_content = {
            "messages": [
                AIMessage(content="", id="empty-ai"),
            ]
        }

        # Act
        result = _extract_mcp_response_content(response_with_empty_content)

        # Assert
        assert result == ""

    def test_extract_content_not_dict_input(self):
        """Test error handling when input is not a dictionary."""
        # Arrange
        invalid_input = "not a dictionary"

        # Act & Assert
        with pytest.raises(
            ValueError,
            match="Invalid MCP response format: missing 'messages' key",
        ):
            _extract_mcp_response_content(invalid_input)

    def test_extract_content_preserves_json_formatting(self):
        """Test that JSON formatting in content is preserved."""
        # Arrange
        json_content = '{\n  "devices": ["xrd-1", "xrd-2"],\n  "count": 2\n}'
        response_with_json = {
            "messages": [
                AIMessage(content=json_content, id="json-ai"),
            ]
        }

        # Act
        result = _extract_mcp_response_content(response_with_json)

        # Assert
        assert result == json_content
        # Verify that newlines and formatting are preserved
        assert "\n" in result
        assert "  " in result  # Check for indentation

    def test_extract_content_real_mcp_structure(self):
        """Test with the exact structure from the real MCP response data."""
        # This test verifies the function works with the actual data structure
        # we expect from the MCP system

        # Act
        result = _extract_mcp_response_content(mpc_response)

        # Assert
        # Verify it's valid JSON-like content
        assert result.startswith("{")
        assert result.endswith("}")
        assert '"device_name"' in result
        assert '"xrd-1"' in result

        # Verify exact content matches what's in the test data
        expected_last_ai_content = '{\n  "device_name": "xrd-1"\n}'
        assert result == expected_last_ai_content
