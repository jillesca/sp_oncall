"""This module provides tools for network operations with gNMIBuddy.

These tools allow interacting with network devices via gNMI (gRPC Network Management Interface)
and OpenConfig models, facilitating diagnostic capabilities for the agent architecture.
"""

from typing import Any, Callable, Dict, List, Optional, Union
from langchain_core.tools import tool

from sp_oncall.configuration import Configuration


# This is a placeholder. In production, these tools would be obtained from the MCP client,
# but we define placeholders here to ensure types are available for documentation.


@tool
def get_devices() -> List[str]:
    """
    Retrieves a list of all network devices available in the inventory.

    Returns:
        A list of device names that can be used in other gNMIBuddy functions.
    """
    # Placeholder that would be implemented via MCP in production
    return ["xrd-1", "xrd-2", "core-rtr-1", "pe1", "pe2"]


@tool
def get_interface_info(
    device_name: str, interface_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve interface information from a network device using gNMI.

    Args:
        device_name: The name of the target device.
        interface_name: Optional specific interface name. If not provided, returns information for all interfaces.

    Returns:
        A dictionary containing interface information.
    """
    # Placeholder that would be implemented via MCP in production
    return {
        "status": "success",
        "data": {
            "interfaces": [
                {
                    "name": "GigabitEthernet0/0/0",
                    "admin_status": "up",
                    "oper_status": "up",
                    "speed": "1Gb",
                }
            ]
        },
    }


@tool
def get_routing_info(
    device_name: str, protocol: str, detail: bool = False
) -> Dict[str, Any]:
    """
    Retrieve routing information from a network device using gNMI.

    Args:
        device_name: The name of the target device.
        protocol: The routing protocol (e.g., "bgp", "ospf", "static").
        detail: Whether to retrieve detailed information.

    Returns:
        A dictionary containing routing information.
    """
    # Placeholder that would be implemented via MCP in production
    return {
        "status": "success",
        "data": f"Routing information for {protocol} on {device_name}",
    }


# Define the list of available tools
TOOLS: List[Callable[..., Any]] = [
    get_devices,
    get_interface_info,
    get_routing_info,
]
