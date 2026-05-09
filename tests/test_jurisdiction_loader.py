"""
Unit tests for the jurisdiction loader.
"""
import pytest
from backend.app.services.jurisdiction_loader import load_jurisdiction, list_available_jurisdictions


class TestJurisdictionLoader:
    def test_load_wisconsin(self):
        rules = load_jurisdiction("WI")
        assert rules["state"] == "WI"
        assert rules["annual_meeting_required"] is True
        assert rules["default_notice_period_days"] >= 10
        assert rules["proxy_permitted"] is True
        assert "notice_notes" in rules

    def test_load_illinois(self):
        rules = load_jurisdiction("IL")
        assert rules["state"] == "IL"
        assert rules["annual_meeting_required"] is True

    def test_unknown_state_returns_defaults(self):
        rules = load_jurisdiction("ZZ")
        assert rules["state"] == "ZZ"
        assert "notice_notes" in rules
        assert "No jurisdiction file found" in rules["notice_notes"]
        # Should have sensible defaults
        assert rules["default_notice_period_days"] > 0

    def test_case_insensitive(self):
        rules_upper = load_jurisdiction("WI")
        rules_lower = load_jurisdiction("wi")
        assert rules_upper["state"] == rules_lower["state"]

    def test_list_available_includes_wi(self):
        available = list_available_jurisdictions()
        assert "WI" in available

    def test_wisconsin_has_proxy_language(self):
        rules = load_jurisdiction("WI")
        assert rules.get("default_proxy_language"), "Wisconsin should have default proxy language"
        assert "KNOW ALL PERSONS" in rules["default_proxy_language"]

    def test_wisconsin_org_meeting_note(self):
        rules = load_jurisdiction("WI")
        assert rules.get("include_org_meeting_note") is True
