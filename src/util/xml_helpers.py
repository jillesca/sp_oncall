"""XML wrapping utilities for LLM prompt data sections.

Injected data sections (device context, trigger context, neighbor results, etc.)
are wrapped in XML tags so LLMs have explicit scope boundaries between
instructions and data. Instructions remain in plain markdown; only dynamic
data sections receive XML tags.
"""


def xml_wrap(tag: str, content: str) -> str:
    """Wrap content in an XML tag pair with inner markdown preserved.

    Args:
        tag: XML tag name (e.g. "device_context", "trigger_context").
        content: Content to wrap, typically markdown-formatted.

    Returns:
        Content enclosed in opening and closing XML tags.
    """
    return f"<{tag}>\n{content}\n</{tag}>"
