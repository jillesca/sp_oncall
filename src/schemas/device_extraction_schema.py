import json
from dataclasses import dataclass, asdict


@dataclass
class DeviceNameExtractionResponse:
    """
    Structured output schema for device name extraction.

    Attributes:
        device_name: The extracted device name from the user query.
        messages: Additional messages or context from the extraction process.
    """

    device_name: str
    messages: str = ""

    def __str__(self) -> str:
        """Return a JSON representation of the device extraction response."""
        return json.dumps(asdict(self), indent=2, default=str)

    def __repr__(self) -> str:
        """Return a detailed representation for debugging."""
        return f"DeviceNameExtractionResponse(device_name='{self.device_name}', messages='{self.messages[:30]}...')"
