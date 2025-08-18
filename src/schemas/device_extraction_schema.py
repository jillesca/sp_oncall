import json
from dataclasses import dataclass, asdict, field
from typing import List, Optional


@dataclass
class DeviceInfo:
    """Information about a single device identified in user query.

    Attributes:
        device_name: The extracted device name.
        device_profile: Device type/model information if determinable.
        priority: Suggested investigation priority based on context.
        dependencies: Other device names this investigation should wait for.
        confidence: Confidence level of device identification (0.0-1.0).
    """

    device_name: str
    device_profile: str = ""
    priority: str = "medium"  # "high", "medium", "low"
    dependencies: List[str] = field(default_factory=list)
    confidence: float = 1.0

    def __str__(self) -> str:
        """Return a JSON representation of the device info."""
        return json.dumps(asdict(self), indent=2, default=str)

    def __repr__(self) -> str:
        """Return a detailed representation for debugging."""
        return f"DeviceInfo(device_name='{self.device_name}', profile='{self.device_profile}', priority={self.priority})"


@dataclass
class MultiDeviceExtractionResponse:
    """Structured output schema for multi-device extraction.

    Attributes:
        devices: List of devices identified in the user query.
        investigation_scope: Description of what type of investigation is needed.
        messages: Additional context or reasoning from the extraction process.
    """

    devices: List[DeviceInfo] = field(default_factory=list)
    investigation_scope: str = ""
    messages: str = ""

    def __str__(self) -> str:
        """Return a JSON representation of the multi-device extraction response."""
        return json.dumps(asdict(self), indent=2, default=str)

    def __repr__(self) -> str:
        """Return a detailed representation for debugging."""
        return f"MultiDeviceExtractionResponse(devices={len(self.devices)} devices, scope='{self.investigation_scope[:30]}...')"


@dataclass
class DeviceNameExtractionResponse:
    """Legacy single-device extraction schema - maintained for backward compatibility.

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
