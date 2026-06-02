"""Device capability profile schema.

Structured protocol and feature flags for a network device, sourced from the
get_device_profile_api MCP call during device discovery. Captures what the
device *runs*, as opposed to what it *is* (topology position and role).

Treated as static facts — infrequently changing, same category as role and
neighbours. Always sourced fresh from the current run's MCP data and formatted
into device_context for prompt injection. Never read back from the store into
prompts. Persisted to the store by the reporter at end of run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class DeviceCapabilityProfile:
    """Protocol and feature flags for a network device.

    Attributes:
        nos: Network Operating System variant (e.g. "iosxr", "iosxe", "nxos").
        is_mpls_enabled: Whether MPLS is configured and active.
        is_isis_enabled: Whether IS-IS is configured and active.
        is_bgp_l3vpn_enabled: Whether BGP L3VPN is configured and active.
        is_route_reflector: Whether this device acts as a BGP Route Reflector.
        has_vpn_ipv4_unicast_bgp: Whether VPN IPv4 unicast BGP is configured.
    """

    nos: str = ""
    is_mpls_enabled: bool = False
    is_isis_enabled: bool = False
    is_route_reflector: bool = False
    is_bgp_l3vpn_enabled: bool = False
    has_vpn_ipv4_unicast_bgp: bool = False


def format_capability_profile_for_context(
    profile: Optional[DeviceCapabilityProfile],
) -> str:
    """Format a device capability profile as a human-readable context section.

    Returns an empty string when the profile is absent so callers can safely
    skip appending the section without conditional logic.

    Args:
        profile: Device capability profile, or None if MCP returned no data.

    Returns:
        Formatted string for inclusion in device_context, or empty string.
    """
    if profile is None:
        return ""

    def _enabled(flag: bool) -> str:
        return "enabled" if flag else "disabled"

    lines = [
        "Device Capabilities:",
        f"  NOS: {profile.nos or 'unknown'}",
        f"  MPLS: {_enabled(profile.is_mpls_enabled)}",
        f"  IS-IS: {_enabled(profile.is_isis_enabled)}",
        f"  BGP L3VPN: {_enabled(profile.is_bgp_l3vpn_enabled)}",
        f"  Route Reflector: {'yes' if profile.is_route_reflector else 'no'}",
        f"  VPN IPv4 Unicast BGP: {_enabled(profile.has_vpn_ipv4_unicast_bgp)}",
    ]
    return "\n".join(lines)
