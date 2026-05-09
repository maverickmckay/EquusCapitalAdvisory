"""
Jurisdiction rules loader.

Loads the YAML file for the association's state and returns a flat
dict of rules suitable for use in the validation and packet-generation
pipeline. Falls back to minimal defaults if no jurisdiction file exists.
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, Any, Optional

import yaml

JURISDICTIONS_DIR = Path(__file__).parent.parent.parent / "jurisdictions"


def load_jurisdiction(state_code: str) -> Dict[str, Any]:
    """
    Load rules for the given two-letter US state code (e.g. "WI").
    Returns a flattened dict suitable for direct lookup by rule name.
    """
    code = state_code.strip().upper()
    yaml_path = JURISDICTIONS_DIR / f"{code.lower()}.yaml"

    if not yaml_path.exists():
        return _defaults(code)

    with open(yaml_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not raw:
        return _defaults(code)

    return _flatten(raw, code)


def _flatten(raw: Dict[str, Any], state_code: str) -> Dict[str, Any]:
    """Extract the fields most commonly referenced by the rule engines."""
    out: Dict[str, Any] = {
        "state": state_code,
        "state_name": raw.get("state_name", state_code),
        "display_name": raw.get("display_name", state_code),
    }

    meetings = raw.get("meetings", {})
    out["annual_meeting_required"] = meetings.get("annual_meeting_required", True)
    out["default_notice_period_days"] = meetings.get("default_notice_period_days", 10)
    out["default_notice_period_max_days"] = meetings.get("default_notice_period_max_days", 60)
    out["notice_notes"] = meetings.get("notice_notes", "")
    out["quorum_notes"] = meetings.get("quorum_notes", "")
    out["adjournment_notes"] = meetings.get("adjournment_notes", "")
    out["remote_meeting_permitted"] = meetings.get("remote_meeting_permitted", False)
    out["remote_meeting_notes"] = meetings.get("remote_meeting_notes", "")
    out["notice_methods_permitted"] = meetings.get("notice_methods_permitted", ["us_mail"])

    proxy = raw.get("proxy", {})
    out["proxy_permitted"] = proxy.get("proxy_permitted", True)
    out["proxy_notes"] = proxy.get("proxy_notes", "")
    out["proxy_single_meeting_default"] = proxy.get("proxy_single_meeting_default", True)
    out["proxy_written_required"] = proxy.get("proxy_written_required", True)
    out["proxy_revocable_default"] = proxy.get("proxy_revocable_default", True)
    out["proxy_agent_default"] = proxy.get("proxy_agent_default", "")

    elections = raw.get("elections", {})
    out["election_notes"] = elections.get("election_notes", "")
    out["nomination_notes"] = elections.get("nomination_notes", "")
    out["director_qualifications_notes"] = elections.get("director_qualifications_notes", "")
    out["org_meeting_notes"] = elections.get("organizational_meeting_notes", "")

    financial = raw.get("financial_reporting", {})
    out["annual_report_notes"] = financial.get("annual_report_notes", "")
    out["budget_approval_notes"] = financial.get("budget_approval_notes", "")
    out["reserve_fund_notes"] = financial.get("reserve_fund_notes", "")

    records = raw.get("records", {})
    out["minutes_required"] = records.get("minutes_required", True)
    out["minutes_notes"] = records.get("minutes_notes", "")
    out["records_statute"] = records.get("records_statute", "")

    packet = raw.get("packet_defaults", {})
    out["default_proxy_language"] = packet.get("default_proxy_language", "")
    out["include_org_meeting_note"] = packet.get("include_org_meeting_note", True)
    out["org_meeting_note"] = packet.get("org_meeting_note", "")

    out["doc_hierarchy_notes"] = raw.get("doc_hierarchy_notes", "")
    out["primary_statutes"] = raw.get("primary_statutes", [])

    return out


def _defaults(state_code: str) -> Dict[str, Any]:
    """Minimal safe defaults when no jurisdiction file is available."""
    return {
        "state": state_code,
        "state_name": state_code,
        "display_name": f"{state_code} (No jurisdiction file — using defaults)",
        "annual_meeting_required": True,
        "default_notice_period_days": 10,
        "default_notice_period_max_days": 60,
        "notice_notes": f"No jurisdiction file found for {state_code}. Verify notice requirements with qualified local counsel.",
        "quorum_notes": "Quorum set by governing documents. No jurisdiction default available.",
        "adjournment_notes": "",
        "remote_meeting_permitted": False,
        "remote_meeting_notes": "",
        "notice_methods_permitted": ["us_mail"],
        "proxy_permitted": True,
        "proxy_notes": "Proxy rules set by governing documents.",
        "proxy_single_meeting_default": True,
        "proxy_written_required": True,
        "proxy_revocable_default": True,
        "proxy_agent_default": "",
        "election_notes": "",
        "nomination_notes": "",
        "director_qualifications_notes": "",
        "org_meeting_notes": "",
        "annual_report_notes": "",
        "budget_approval_notes": "",
        "reserve_fund_notes": "",
        "minutes_required": True,
        "minutes_notes": "",
        "records_statute": "",
        "default_proxy_language": "",
        "include_org_meeting_note": True,
        "org_meeting_note": "",
        "doc_hierarchy_notes": "",
        "primary_statutes": [],
    }


def list_available_jurisdictions() -> list[str]:
    """Return list of state codes with jurisdiction files."""
    if not JURISDICTIONS_DIR.exists():
        return []
    return sorted([
        p.stem.upper()
        for p in JURISDICTIONS_DIR.glob("*.yaml")
        if p.stem not in ("__init__",)
    ])
