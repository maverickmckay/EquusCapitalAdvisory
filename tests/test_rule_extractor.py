"""
Unit tests for the rule extraction engine.

Tests verify that the extractor correctly identifies governance rules
from typical governing-document language patterns.
"""
import pytest
from backend.app.models.document import ParsedDocument, DocumentType
from backend.app.services.rule_extractor import (
    extract_rules,
    extract_notice_period,
    extract_notice_max_period,
    extract_quorum,
    extract_proxy_rules,
    extract_election_rules,
    extract_meeting_requirement,
    extract_org_meeting_requirement,
    extract_vote_per_unit,
)

DOC_ID = "test-doc-001"


def _make_parsed(text: str, doc_type=DocumentType.BYLAWS) -> ParsedDocument:
    return ParsedDocument(
        document_id=DOC_ID,
        document_type=doc_type,
        full_text=text,
    )


# ---------------------------------------------------------------------------
# Notice period extraction
# ---------------------------------------------------------------------------
class TestNoticePeriod:
    def test_not_less_than_15_days(self):
        text = "Written notice shall be given to each unit owner not less than fifteen (15) days before the meeting."
        rules = extract_notice_period(text, DOC_ID)
        assert len(rules) >= 1
        assert rules[0].canonical_field == "notice_period_days"
        assert rules[0].value == 15

    def test_at_least_10_days(self):
        text = "Notice shall be given at least 10 days prior to the meeting."
        rules = extract_notice_period(text, DOC_ID)
        assert len(rules) >= 1
        assert rules[0].value == 10

    def test_21_day_notice(self):
        text = "Notice of the annual meeting must be mailed not less than 21 days in advance."
        rules = extract_notice_period(text, DOC_ID)
        assert len(rules) >= 1
        assert rules[0].value == 21

    def test_no_notice_language(self):
        text = "The association shall hold meetings. All owners may attend."
        rules = extract_notice_period(text, DOC_ID)
        assert rules == []

    def test_max_notice_period(self):
        text = "Notice shall be given not less than 15 days nor more than 60 days before the meeting."
        rules = extract_notice_max_period(text, DOC_ID)
        assert len(rules) >= 1
        assert rules[0].value == 60


# ---------------------------------------------------------------------------
# Quorum extraction
# ---------------------------------------------------------------------------
class TestQuorum:
    def test_percentage_quorum_numeric(self):
        text = "A quorum shall be twenty-five percent (25%) of the total votes of the Association."
        rules = extract_quorum(text, DOC_ID)
        assert len(rules) >= 1
        r = next(r for r in rules if r.canonical_field == "quorum_threshold_pct")
        assert r.value == 25.0

    def test_percentage_quorum_word(self):
        text = "Owners entitled to cast 33% of the total votes shall constitute a quorum."
        rules = extract_quorum(text, DOC_ID)
        assert len(rules) >= 1
        assert rules[0].value == 33.0

    def test_fractional_quorum_one_third(self):
        text = "One-third of the members entitled to vote shall constitute a quorum for the transaction of business."
        rules = extract_quorum(text, DOC_ID)
        assert len(rules) >= 1
        r = rules[0]
        assert r.canonical_field == "quorum_threshold_pct"
        assert abs(r.value - 33.33) < 0.1
        assert r.is_ambiguous  # fraction was converted

    def test_majority_quorum(self):
        text = "A majority of the members present shall constitute a quorum."
        rules = extract_quorum(text, DOC_ID)
        assert len(rules) >= 1
        assert rules[0].value == 50.01


# ---------------------------------------------------------------------------
# Proxy rule extraction
# ---------------------------------------------------------------------------
class TestProxyRules:
    def test_proxy_permitted(self):
        text = "A unit owner may vote by proxy. Every proxy shall be in writing."
        rules = extract_proxy_rules(text, DOC_ID)
        proxy_rule = next((r for r in rules if r.canonical_field == "proxy_permitted"), None)
        assert proxy_rule is not None
        assert proxy_rule.value is True

    def test_single_meeting_proxy(self):
        text = "A proxy shall be effective only for the specific meeting for which it is given."
        rules = extract_proxy_rules(text, DOC_ID)
        single = next((r for r in rules if r.canonical_field == "proxy_single_meeting"), None)
        assert single is not None
        assert single.value is True

    def test_no_proxy_language_flags_ambiguous(self):
        text = "The board shall manage the affairs of the association."
        rules = extract_proxy_rules(text, DOC_ID)
        proxy_rule = next((r for r in rules if r.canonical_field == "proxy_permitted"), None)
        assert proxy_rule is not None
        assert proxy_rule.value is False
        assert proxy_rule.is_ambiguous


# ---------------------------------------------------------------------------
# Election rule extraction
# ---------------------------------------------------------------------------
class TestElectionRules:
    def test_annual_election(self):
        text = "Directors shall be elected by the unit owners at each annual meeting."
        rules = extract_election_rules(text, DOC_ID)
        r = next((r for r in rules if r.canonical_field == "election_at_annual_meeting"), None)
        assert r is not None
        assert r.value is True

    def test_three_year_term(self):
        text = "Directors shall serve three-year terms."
        rules = extract_election_rules(text, DOC_ID)
        r = next((r for r in rules if r.canonical_field == "director_term_years"), None)
        assert r is not None
        assert r.value == 3

    def test_staggered_terms(self):
        text = "The terms of directors shall be staggered so that not all seats expire in the same year."
        rules = extract_election_rules(text, DOC_ID)
        r = next((r for r in rules if r.canonical_field == "staggered_terms"), None)
        assert r is not None
        assert r.value is True

    def test_board_size(self):
        text = "The Board of Directors shall consist of five (5) directors."
        rules = extract_election_rules(text, DOC_ID)
        r = next((r for r in rules if r.canonical_field == "board_size"), None)
        assert r is not None
        assert r.value == 5

    def test_floor_nominations(self):
        text = "Nominations may also be made from the floor at the annual meeting."
        rules = extract_election_rules(text, DOC_ID)
        r = next((r for r in rules if r.canonical_field == "nominations_from_floor"), None)
        assert r is not None
        assert r.value is True


# ---------------------------------------------------------------------------
# Full extraction pipeline
# ---------------------------------------------------------------------------
class TestFullExtraction:
    def test_bylaws_full_extraction(self):
        """Integration test: extract multiple rules from a realistic bylaws excerpt."""
        bylaws_text = """
        ARTICLE III — MEETINGS

        Section 3.1 Annual Meeting. An annual meeting of unit owners shall be held each year
        for the purpose of electing directors and for the transaction of other business.

        Section 3.2 Notice. Written notice shall be given not less than fifteen (15) days
        nor more than sixty (60) days before the meeting.

        Section 3.3 Quorum. Owners entitled to cast twenty-five percent (25%) of the total
        votes shall constitute a quorum.

        Section 3.4 Voting. Each unit shall have one (1) vote per unit.

        Section 3.5 Proxies. A unit owner may vote by proxy. A proxy shall be effective
        only for the specific meeting for which it is given.

        ARTICLE IV — DIRECTORS
        Directors shall be elected at the annual meeting and shall serve three-year (3-year)
        staggered terms. The Board shall consist of five (5) directors.

        Immediately following the annual meeting of unit owners, the Board of Directors
        shall hold an organizational meeting.
        """
        parsed = _make_parsed(bylaws_text)
        rules = extract_rules(parsed)
        rule_map = {r.canonical_field: r for r in rules}

        assert "notice_period_days" in rule_map
        assert rule_map["notice_period_days"].value == 15

        assert "quorum_threshold_pct" in rule_map
        assert rule_map["quorum_threshold_pct"].value == 25.0

        assert "proxy_permitted" in rule_map
        assert rule_map["proxy_permitted"].value is True

        assert "proxy_single_meeting" in rule_map
        assert rule_map["proxy_single_meeting"].value is True

        assert "director_term_years" in rule_map
        assert rule_map["director_term_years"].value == 3

        assert "staggered_terms" in rule_map
        assert rule_map["staggered_terms"].value is True

        assert "board_size" in rule_map
        assert rule_map["board_size"].value == 5

        assert "org_meeting_after_annual" in rule_map
        assert rule_map["org_meeting_after_annual"].value is True

        assert "vote_structure" in rule_map
        assert rule_map["vote_structure"].value == "one_vote_per_unit"

    def test_deduplication_keeps_high_confidence(self):
        """When two extractors produce the same field, keep higher confidence."""
        text = "Notice of at least 15 days is required. Notice shall be given not less than fifteen (15) days."
        parsed = _make_parsed(text)
        rules = extract_rules(parsed)
        notice_rules = [r for r in rules if r.canonical_field == "notice_period_days"]
        assert len(notice_rules) == 1, "Deduplication should produce exactly one notice_period_days rule"
