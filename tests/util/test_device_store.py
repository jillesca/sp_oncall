"""
Unit tests for the device_store utility.

Tests use a real InMemoryStore to verify the read/write contract,
rather than mocking the store internals.
"""

import pytest
from langgraph.store.memory import InMemoryStore

from src.util.device_store import (
    get_device_profile,
    update_device_profile,
    format_dynamic_facts_for_context,
    get_device_history,
    append_device_history,
    build_history_summary,
    format_history_for_context,
)


@pytest.fixture()
def store() -> InMemoryStore:
    return InMemoryStore()


class TestGetDeviceProfile:
    def test_returns_empty_dict_when_no_profile_exists(self, store):
        result = get_device_profile(store, "xrd-1")
        assert result == {}

    def test_returns_empty_dict_when_store_is_none(self):
        result = get_device_profile(None, "xrd-1")
        assert result == {}

    def test_returns_stored_profile(self, store):
        store.put(("device_profiles", "xrd-1"), "profile", {"static_facts": {"role": "PE"}})
        result = get_device_profile(store, "xrd-1")
        assert result == {"static_facts": {"role": "PE"}}

    def test_isolates_profiles_by_device_name(self, store):
        store.put(("device_profiles", "xrd-1"), "profile", {"static_facts": {"role": "PE"}})
        store.put(("device_profiles", "xrd-2"), "profile", {"static_facts": {"role": "P"}})

        assert get_device_profile(store, "xrd-1")["static_facts"]["role"] == "PE"
        assert get_device_profile(store, "xrd-2")["static_facts"]["role"] == "P"
        assert get_device_profile(store, "xrd-3") == {}


class TestUpdateDeviceProfile:
    def test_saves_static_facts(self, store):
        update_device_profile(store, "xrd-1", static_facts={"role": "PE", "bgp_as": 65001})

        profile = get_device_profile(store, "xrd-1")
        assert profile["static_facts"]["role"] == "PE"
        assert profile["static_facts"]["bgp_as"] == 65001

    def test_saves_dynamic_facts(self, store):
        update_device_profile(
            store,
            "xrd-1",
            dynamic_facts={"last_alert": "interface down", "last_known_state": "completed"},
        )

        profile = get_device_profile(store, "xrd-1")
        assert profile["dynamic_facts"]["last_alert"] == "interface down"
        assert profile["dynamic_facts"]["last_known_state"] == "completed"

    def test_merges_static_facts_with_existing(self, store):
        update_device_profile(store, "xrd-1", static_facts={"role": "PE"})
        update_device_profile(store, "xrd-1", static_facts={"bgp_as": 65001})

        profile = get_device_profile(store, "xrd-1")
        assert profile["static_facts"]["role"] == "PE"
        assert profile["static_facts"]["bgp_as"] == 65001

    def test_merges_dynamic_facts_with_existing(self, store):
        update_device_profile(store, "xrd-1", dynamic_facts={"last_alert": "first alert"})
        update_device_profile(store, "xrd-1", dynamic_facts={"last_known_state": "completed"})

        profile = get_device_profile(store, "xrd-1")
        assert profile["dynamic_facts"]["last_alert"] == "first alert"
        assert profile["dynamic_facts"]["last_known_state"] == "completed"

    def test_overwrites_existing_key_in_same_fact_group(self, store):
        update_device_profile(store, "xrd-1", dynamic_facts={"last_alert": "old alert"})
        update_device_profile(store, "xrd-1", dynamic_facts={"last_alert": "new alert"})

        profile = get_device_profile(store, "xrd-1")
        assert profile["dynamic_facts"]["last_alert"] == "new alert"

    def test_saves_both_static_and_dynamic_in_one_call(self, store):
        update_device_profile(
            store,
            "xrd-1",
            static_facts={"role": "PE"},
            dynamic_facts={"last_known_state": "completed"},
        )

        profile = get_device_profile(store, "xrd-1")
        assert profile["static_facts"]["role"] == "PE"
        assert profile["dynamic_facts"]["last_known_state"] == "completed"

    def test_does_nothing_when_store_is_none(self):
        update_device_profile(None, "xrd-1", static_facts={"role": "PE"})

    def test_does_nothing_when_no_facts_provided(self, store):
        update_device_profile(store, "xrd-1")
        assert get_device_profile(store, "xrd-1") == {}

    def test_isolates_updates_by_device_name(self, store):
        update_device_profile(store, "xrd-1", static_facts={"role": "PE"})
        update_device_profile(store, "xrd-2", static_facts={"role": "P"})

        assert get_device_profile(store, "xrd-1")["static_facts"]["role"] == "PE"
        assert get_device_profile(store, "xrd-2")["static_facts"]["role"] == "P"


class TestGetDeviceHistory:
    def test_returns_empty_list_when_no_history_exists(self, store):
        result = get_device_history(store, "xrd-1")
        assert result == []

    def test_returns_empty_list_when_store_is_none(self):
        result = get_device_history(None, "xrd-1")
        assert result == []

    def test_returns_stored_history_entries(self, store):
        entry = {"timestamp": "2026-01-01T00:00:00+00:00", "status": "completed", "summary": "All good"}
        store.put(("device_profiles", "xrd-1"), "history", {"entries": [entry]})

        result = get_device_history(store, "xrd-1")

        assert len(result) == 1
        assert result[0]["status"] == "completed"

    def test_respects_limit_parameter(self, store):
        entries = [
            {"timestamp": f"2026-01-0{i}T00:00:00+00:00", "status": "completed", "summary": f"Run {i}"}
            for i in range(1, 6)
        ]
        store.put(("device_profiles", "xrd-1"), "history", {"entries": entries})

        result = get_device_history(store, "xrd-1", limit=3)

        assert len(result) == 3
        assert result[0]["summary"] == "Run 3"
        assert result[-1]["summary"] == "Run 5"

    def test_returns_entries_in_chronological_order(self, store):
        entries = [
            {"timestamp": "2026-01-01T00:00:00+00:00", "status": "completed", "summary": "First"},
            {"timestamp": "2026-01-02T00:00:00+00:00", "status": "failed", "summary": "Second"},
        ]
        store.put(("device_profiles", "xrd-1"), "history", {"entries": entries})

        result = get_device_history(store, "xrd-1", limit=5)

        assert result[0]["summary"] == "First"
        assert result[1]["summary"] == "Second"

    def test_isolates_history_by_device_name(self, store):
        store.put(("device_profiles", "xrd-1"), "history", {"entries": [{"summary": "xrd-1 run"}]})
        store.put(("device_profiles", "xrd-2"), "history", {"entries": [{"summary": "xrd-2 run"}]})

        assert get_device_history(store, "xrd-1")[0]["summary"] == "xrd-1 run"
        assert get_device_history(store, "xrd-2")[0]["summary"] == "xrd-2 run"
        assert get_device_history(store, "xrd-3") == []


class TestAppendDeviceHistory:
    def test_appends_entry_to_empty_history(self, store):
        summary = {"timestamp": "2026-01-01T00:00:00+00:00", "status": "completed", "summary": "First run"}
        append_device_history(store, "xrd-1", summary)

        result = get_device_history(store, "xrd-1")
        assert len(result) == 1
        assert result[0]["status"] == "completed"

    def test_appends_entry_to_existing_history(self, store):
        first = {"timestamp": "2026-01-01T00:00:00+00:00", "status": "completed", "summary": "First"}
        second = {"timestamp": "2026-01-02T00:00:00+00:00", "status": "failed", "summary": "Second"}
        append_device_history(store, "xrd-1", first)
        append_device_history(store, "xrd-1", second)

        result = get_device_history(store, "xrd-1")
        assert len(result) == 2
        assert result[-1]["summary"] == "Second"

    def test_caps_history_at_max_size(self, store):
        for i in range(12):
            append_device_history(store, "xrd-1", {"timestamp": f"t{i}", "status": "completed", "summary": f"Run {i}"})

        result = get_device_history(store, "xrd-1", limit=20)
        assert len(result) == 10
        assert result[0]["summary"] == "Run 2"
        assert result[-1]["summary"] == "Run 11"

    def test_does_nothing_when_store_is_none(self):
        append_device_history(None, "xrd-1", {"summary": "ignored"})

    def test_isolates_appends_by_device_name(self, store):
        append_device_history(store, "xrd-1", {"summary": "xrd-1"})
        append_device_history(store, "xrd-2", {"summary": "xrd-2"})

        assert get_device_history(store, "xrd-1")[0]["summary"] == "xrd-1"
        assert get_device_history(store, "xrd-2")[0]["summary"] == "xrd-2"


class TestBuildHistorySummary:
    def test_includes_timestamp_status_and_summary(self):
        result = build_history_summary(status="completed", report="All interfaces are up.")

        assert result["status"] == "completed"
        assert result["summary"] == "All interfaces are up."
        assert "timestamp" in result

    def test_truncates_report_to_1000_chars(self):
        long_report = "x" * 2000
        result = build_history_summary(status="completed", report=long_report)

        assert len(result["summary"]) == 1000

    def test_handles_none_report(self):
        result = build_history_summary(status="failed", report=None)

        assert result["summary"] == ""
        assert result["status"] == "failed"


class TestFormatDynamicFactsForContext:
    def test_returns_empty_string_for_empty_profile(self):
        result = format_dynamic_facts_for_context({})
        assert result == ""

    def test_returns_empty_string_when_no_dynamic_facts(self):
        profile = {"static_facts": {"role": "PE", "bgp_as": 65001}}
        result = format_dynamic_facts_for_context(profile)
        assert result == ""

    def test_formats_dynamic_facts(self):
        profile = {"dynamic_facts": {"last_alert": "interface down"}}
        result = format_dynamic_facts_for_context(profile)

        assert "Previous Investigation Context:" in result
        assert "last_alert: interface down" in result

    def test_formats_multiple_dynamic_facts(self):
        profile = {
            "dynamic_facts": {
                "last_alert": "bgp session down",
                "last_known_state": "completed",
            }
        }
        result = format_dynamic_facts_for_context(profile)

        assert "Previous Investigation Context:" in result
        assert "last_alert: bgp session down" in result
        assert "last_known_state: completed" in result

    def test_ignores_static_facts(self):
        profile = {
            "static_facts": {"role": "PE"},
            "dynamic_facts": {"last_known_state": "completed"},
        }
        result = format_dynamic_facts_for_context(profile)

        assert "Static Device Facts:" not in result
        assert "role: PE" not in result
        assert "Previous Investigation Context:" in result
        assert "last_known_state: completed" in result

    def test_returns_string_type(self):
        result = format_dynamic_facts_for_context(
            {"dynamic_facts": {"last_known_state": "completed"}}
        )
        assert isinstance(result, str)


class TestFormatHistoryForContext:
    def test_returns_empty_string_for_empty_history(self):
        result = format_history_for_context([])
        assert result == ""

    def test_formats_single_entry(self):
        history = [{"timestamp": "2026-01-01T00:00:00+00:00", "status": "completed", "summary": "All good"}]
        result = format_history_for_context(history)

        assert "Previous Investigation Findings:" in result
        assert "2026-01-01T00:00:00+00:00" in result
        assert "completed" in result
        assert "All good" in result

    def test_formats_multiple_entries_with_sequential_numbering(self):
        history = [
            {"timestamp": "2026-01-01T00:00:00+00:00", "status": "completed", "summary": "First run"},
            {"timestamp": "2026-01-02T00:00:00+00:00", "status": "failed", "summary": "Second run"},
        ]
        result = format_history_for_context(history)

        assert "[1]" in result
        assert "[2]" in result
        assert "First run" in result
        assert "Second run" in result

    def test_handles_missing_fields_gracefully(self):
        history = [{"summary": "Partial entry"}]
        result = format_history_for_context(history)

        assert "Previous Investigation Findings:" in result
        assert "Partial entry" in result
        assert "unknown" in result

    def test_returns_string_type(self):
        history = [{"timestamp": "t", "status": "completed", "summary": "s"}]
        result = format_history_for_context(history)
        assert isinstance(result, str)
