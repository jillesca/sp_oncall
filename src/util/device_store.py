"""
Device profile storage using LangGraph Store.

Provides read/write access to per-device profiles persisted across graph runs.
Profiles hold both stable device metadata (static_facts) and recent investigation
findings (dynamic_facts), enabling historical context across alert threads.
History tracks the last N investigation summaries per device, surfaced as
"previous findings" when the executor builds context for a new investigation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langgraph.store.base import BaseStore

from src.logging import get_logger

logger = get_logger(__name__)

_PROFILE_KEY = "profile"
_HISTORY_KEY = "history"
_MAX_HISTORY_SIZE = 10


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


def format_dynamic_facts_for_context(profile: dict[str, Any]) -> str:
    """Format stored dynamic facts as human-readable text for prompt injection.

    Only formats dynamic_facts (recent investigation findings). Static facts are
    always sourced fresh from MCP discovery and never read back from the store
    into prompts to avoid stale topology data.

    Args:
        profile: Profile dict from get_device_profile

    Returns:
        Formatted string for inclusion in investigation context, or empty string
        if no dynamic facts exist.
    """
    if not profile:
        return ""

    dynamic = profile.get("dynamic_facts")
    if not dynamic:
        return ""

    lines = ["Previous Investigation Context:"]
    for key, value in dynamic.items():
        lines.append(f"  {key}: {value}")

    return "\n".join(lines)


def get_device_history(
    store: BaseStore | None,
    device_name: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Return the last N investigation summaries for a device.

    Returns summaries in chronological order (oldest first) so the LLM reads
    them as a natural timeline. Returns an empty list if no history exists or
    no store is configured.

    Args:
        store: LangGraph BaseStore instance, or None if not configured
        device_name: Device identifier
        limit: Maximum number of recent entries to return
    """
    if store is None:
        return []

    item = store.get(_device_namespace(device_name), _HISTORY_KEY)
    if item is None:
        logger.debug("No stored history for device: %s", device_name)
        return []

    entries = item.value.get("entries", [])
    logger.debug(
        "Loaded %d history entries for device: %s", len(entries), device_name
    )
    return entries[-limit:]


def append_device_history(
    store: BaseStore | None,
    device_name: str,
    summary: dict[str, Any],
) -> None:
    """Append an investigation summary to the device's history.

    Keeps only the last _MAX_HISTORY_SIZE entries to prevent unbounded growth.
    Each summary should include 'timestamp', 'status', and 'summary' keys.
    Does nothing if no store is configured.

    Args:
        store: LangGraph BaseStore instance, or None if not configured
        device_name: Device identifier
        summary: Investigation summary dict with timestamp, status, and summary fields
    """
    if store is None:
        return

    item = store.get(_device_namespace(device_name), _HISTORY_KEY)
    existing_entries = item.value.get("entries", []) if item is not None else []

    updated_entries = (existing_entries + [summary])[-_MAX_HISTORY_SIZE:]
    store.put(
        _device_namespace(device_name), _HISTORY_KEY, {"entries": updated_entries}
    )
    logger.debug("Appended history entry for device: %s", device_name)


def build_history_summary(status: str, report: str | None) -> dict[str, Any]:
    """Build a history summary dict from an investigation result.

    Args:
        status: Investigation status value (e.g. "completed", "failed")
        report: Investigation report text, truncated to 1000 characters

    Returns:
        Summary dict ready for append_device_history
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "summary": (report or "")[:1000],
    }


def format_history_for_context(history: list[dict[str, Any]]) -> str:
    """Format device investigation history as human-readable text for prompt injection.

    Args:
        history: List of history entry dicts from get_device_history

    Returns:
        Formatted string for inclusion in investigation context, or empty string
        if history is empty.
    """
    if not history:
        return ""

    lines = ["Previous Investigation Findings:"]
    for i, entry in enumerate(history, start=1):
        timestamp = entry.get("timestamp", "unknown")
        status = entry.get("status", "unknown")
        summary = entry.get("summary", "")
        lines.append(f"  [{i}] {timestamp} (status: {status}):")
        lines.append(f"    {summary}")

    return "\n".join(lines)
