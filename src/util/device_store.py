"""
Device profile storage using LangGraph Store.

Provides read/write access to per-device profiles persisted across graph runs.
Profiles hold both stable device metadata (static_facts) and recent investigation
findings (dynamic_facts), enabling historical context across alert threads.
"""

from __future__ import annotations

from typing import Any

from langgraph.store.base import BaseStore

from src.logging import get_logger

logger = get_logger(__name__)

_PROFILE_KEY = "profile"


def _device_namespace(device_name: str) -> tuple[str, str]:
    return ("device_profiles", device_name)


def get_device_profile(store: BaseStore | None, device_name: str) -> dict[str, Any]:
    """Read the stored profile for a device.

    Returns a dict with 'static_facts' and/or 'dynamic_facts' keys,
    or an empty dict if no profile has been saved yet or no store is configured.

    Args:
        store: LangGraph BaseStore instance, or None if not configured
        device_name: Device identifier
    """
    if store is None:
        return {}

    item = store.get(_device_namespace(device_name), _PROFILE_KEY)
    if item is None:
        logger.debug("No stored profile for device: %s", device_name)
        return {}

    logger.debug("Loaded stored profile for device: %s", device_name)
    return item.value


def update_device_profile(
    store: BaseStore | None,
    device_name: str,
    *,
    static_facts: dict[str, Any] | None = None,
    dynamic_facts: dict[str, Any] | None = None,
) -> None:
    """Merge new facts into a device's stored profile.

    Static facts (role, ISIS area, BGP AS, direct neighbours, interfaces) are
    stable device metadata. Dynamic facts (last_alert, last_known_state,
    last_investigation_summary) capture recent investigation findings.

    Each call merges into the existing profile rather than replacing it.
    Does nothing if no store is configured or no facts are provided.

    Args:
        store: LangGraph BaseStore instance, or None if not configured
        device_name: Device identifier
        static_facts: Stable device metadata to persist
        dynamic_facts: Recent investigation findings to persist
    """
    if store is None or (static_facts is None and dynamic_facts is None):
        return

    existing = get_device_profile(store, device_name)
    updated = dict(existing)

    if static_facts:
        updated["static_facts"] = {
            **existing.get("static_facts", {}),
            **static_facts,
        }

    if dynamic_facts:
        updated["dynamic_facts"] = {
            **existing.get("dynamic_facts", {}),
            **dynamic_facts,
        }

    store.put(_device_namespace(device_name), _PROFILE_KEY, updated)
    logger.debug("Updated profile for device: %s", device_name)


def format_profile_for_context(profile: dict[str, Any]) -> str:
    """Format a stored device profile as human-readable text for prompt injection.

    Args:
        profile: Profile dict from get_device_profile

    Returns:
        Formatted string for inclusion in investigation context, or empty string
        if profile has no useful content.
    """
    if not profile:
        return ""

    lines = []

    if static := profile.get("static_facts"):
        lines.append("Static Device Facts:")
        for key, value in static.items():
            lines.append(f"  {key}: {value}")

    if dynamic := profile.get("dynamic_facts"):
        lines.append("Previous Investigation Context:")
        for key, value in dynamic.items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)
