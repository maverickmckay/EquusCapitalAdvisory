"""
Unit tests for the compliance validation engine.
"""
import pytest
from datetime import date

from backend.app.models.association import AssociationProfile, AssociationType
from backend.app.models.meeting import MeetingProfile
from backend.app.models.packet import (
    ProjectState, ElectionProfile, FinancialProfile,
    BoardMember, BoardSeat, ValidationSeverity
)
from backend.app.services.validator import run_validation, validation_summary, validate_notice_period


def _make_state() -> ProjectState:
    assoc = AssociationProfile(
        association_name="Validation Test HOA",
        state="WI",
        meeting_year=2026,
    )
    state = ProjectState(
        project_name="Validator Test",
        association=assoc,
    )
    state.jurisdiction_rules = {
        "default_notice_period_days": 10,
        "default_notice_period_max_days": 60,
        "include_org_meeting_note": True,
        "org_meeting_note": "",
    }
    return state


class TestNoticeValidation:
    def test_notice_period_pass(self):
        state = _make_state()
        state.meeting.meeting_date = date(2026, 3, 17)
        state.meeting.notice_date = date(2026, 2, 27)
        state.meeting.notice_period_min_days = 15
        result = validate_notice_period(state)
        assert result.severity == ValidationSeverity.PASS

    def test_notice_period_too_short_is_blocker(self):
        state = _make_state()
        state.meeting.meeting_date = date(2026, 3, 17)
        state.meeting.notice_date = date(2026, 3, 15)  # only 2 days
        state.meeting.notice_period_min_days = 15
        result = validate_notice_period(state)
        assert result.severity == ValidationSeverity.BLOCKER

    def test_notice_period_missing_is_warning(self):
        state = _make_state()
        state.meeting.meeting_date = date(2026, 3, 17)
        state.meeting.notice_date = None  # missing
        result = validate_notice_period(state)
        assert result.severity == ValidationSeverity.WARNING

    def test_notice_uses_bylaw_minimum_over_jurisdiction_default(self):
        state = _make_state()
        state.meeting.meeting_date = date(2026, 3, 17)
        state.meeting.notice_date = date(2026, 3, 5)  # 12 days before
        state.meeting.notice_period_min_days = 15  # bylaw says 15
        state.jurisdiction_rules["default_notice_period_days"] = 10  # jurisdiction says 10
        result = validate_notice_period(state)
        # 12 < 15 → blocker
        assert result.severity == ValidationSeverity.BLOCKER


class TestElectionValidation:
    def test_no_election_returns_info(self):
        state = _make_state()
        state.election.election_required = False
        results = run_validation(state)
        election_results = [r for r in results if r.category == "Election"]
        assert any(r.severity == ValidationSeverity.INFO for r in election_results)

    def test_election_with_staggered_no_seat_map_is_blocker(self):
        state = _make_state()
        state.election.election_required = True
        state.election.staggered_terms = True
        state.election.seat_map = []
        state.election.board_roster = []
        results = run_validation(state)
        election_blocks = [r for r in results if r.category == "Election" and r.severity == ValidationSeverity.BLOCKER]
        assert len(election_blocks) >= 1

    def test_election_with_seat_map_passes(self):
        state = _make_state()
        state.election.election_required = True
        state.election.staggered_terms = True
        state.election.seat_map = [
            BoardSeat(seat_label="Seat A", up_for_election=True, current_occupant="Jane Doe")
        ]
        results = run_validation(state)
        election_blocks = [r for r in results if r.category == "Election" and r.severity == ValidationSeverity.BLOCKER]
        assert len(election_blocks) == 0


class TestValidationSummary:
    def test_blockers_block_generation(self):
        state = _make_state()
        state.meeting.meeting_date = date(2026, 3, 17)
        state.meeting.notice_date = date(2026, 3, 16)  # 1 day — blocker
        state.meeting.notice_period_min_days = 15
        results = run_validation(state)
        summary = validation_summary(results)
        assert not summary["ready_to_generate"]
        assert summary["blocker_count"] > 0

    def test_ready_when_no_blockers(self):
        state = _make_state()
        state.meeting.meeting_date = date(2026, 3, 17)
        state.meeting.notice_date = date(2026, 2, 26)  # 19 days — ok
        state.meeting.notice_period_min_days = 15
        state.meeting.meeting_time = "6:00 PM"
        state.meeting.meeting_location = "Community Room"
        state.meeting.quorum_threshold = 25.0
        state.election.election_required = False
        state.financial.approved_budget_total = 100000.0
        state.financial.prior_year_end_net = 500.0
        state.election.board_roster = [BoardMember(name="Alice", unit_number="101")]
        results = run_validation(state)
        summary = validation_summary(results)
        assert summary["ready_to_generate"], f"Blockers: {summary['blockers']}"
