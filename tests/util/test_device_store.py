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
    format_profile_for_context,
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


class TestFormatProfileForContext:
    def test_returns_empty_string_for_empty_profile(self):
        result = format_profile_for_context({})
        assert result == ""

    def test_formats_static_facts(self):
        profile = {"static_facts": {"role": "PE", "bgp_as": 65001}}
        result = format_profile_for_context(profile)

        assert "Static Device Facts:" in result
        assert "role: PE" in result
        assert "bgp_as: 65001" in result

    def test_formats_dynamic_facts(self):
        profile = {"dynamic_facts": {"last_alert": "interface down"}}
        result = format_profile_for_context(profile)

        assert "Previous Investigation Context:" in result
        assert "last_alert: interface down" in result

    def test_formats_both_static_and_dynamic(self):
        profile = {
            "static_facts": {"role": "PE"},
            "dynamic_facts": {"last_known_state": "completed"},
        }
        result = format_profile_for_context(profile)

        assert "Static Device Facts:" in result
        assert "role: PE" in result
        assert "Previous Investigation Context:" in result
        assert "last_known_state: completed" in result

    def test_returns_string_type(self):
        result = format_profile_for_context({"static_facts": {"role": "PE"}})
        assert isinstance(result, str)
