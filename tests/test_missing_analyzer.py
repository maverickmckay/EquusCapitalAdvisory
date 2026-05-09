"""
Unit tests for the missing-items analysis engine.
"""
import pytest
from datetime import date

from backend.app.models.association import AssociationProfile, AssociationType
from backend.app.models.meeting import MeetingProfile
from backend.app.models.packet import (
    ProjectState, DocumentStatus, FinancialProfile, ElectionProfile,
    BoardMember, MissingItemSeverity
)
from backend.app.models.document import UploadedDocument, DocumentType
from backend.app.services.missing_analyzer import analyze_missing_items, summarize_missing


def _make_minimal_state() -> ProjectState:
    """State with only basic association info — should trigger many missing items."""
    assoc = AssociationProfile(
        association_name="Test HOA",
        state="WI",
        meeting_year=2026,
    )
    state = ProjectState(
        project_name="Test Project",
        association=assoc,
    )
    return state


def _add_doc(state: ProjectState, doc_type: DocumentType) -> None:
    doc = UploadedDocument(
        filename=f"{doc_type.value}.pdf",
        original_filename=f"{doc_type.value}.pdf",
        document_type=doc_type,
    )
    state.document_status.uploaded_docs.append(doc)


class TestMissingAnalyzer:
    def test_minimal_state_has_blockers(self):
        state = _make_minimal_state()
        analyze_missing_items(state)
        blockers = [i for i in state.document_status.missing_required
                    if i.severity == MissingItemSeverity.BLOCKER]
        assert len(blockers) > 0, "Minimal state should have at least one blocker"

    def test_no_governing_doc_is_blocker(self):
        state = _make_minimal_state()
        analyze_missing_items(state)
        blocker_fields = [i.canonical_field for i in state.document_status.missing_required
                          if i.severity == MissingItemSeverity.BLOCKER]
        assert "governing_document" in blocker_fields

    def test_uploading_bylaws_resolves_governing_doc_blocker(self):
        state = _make_minimal_state()
        _add_doc(state, DocumentType.BYLAWS)
        analyze_missing_items(state)
        blocker_fields = [i.canonical_field for i in state.document_status.missing_required
                          if i.severity == MissingItemSeverity.BLOCKER and i.canonical_field == "governing_document"]
        assert len(blocker_fields) == 0

    def test_missing_meeting_date_is_required(self):
        state = _make_minimal_state()
        analyze_missing_items(state)
        required_fields = [i.canonical_field for i in state.document_status.missing_required]
        assert "meeting_date" in required_fields

    def test_providing_meeting_date_removes_from_required(self):
        state = _make_minimal_state()
        state.meeting.meeting_date = date(2026, 3, 17)
        analyze_missing_items(state)
        required_fields = [i.canonical_field for i in state.document_status.missing_required]
        assert "meeting_date" not in required_fields

    def test_missing_budget_is_required(self):
        state = _make_minimal_state()
        analyze_missing_items(state)
        required_fields = [i.canonical_field for i in state.document_status.missing_required]
        assert "current_budget" in required_fields

    def test_uploading_budget_resolves_required(self):
        state = _make_minimal_state()
        _add_doc(state, DocumentType.CURRENT_BUDGET)
        analyze_missing_items(state)
        required_fields = [i.canonical_field for i in state.document_status.missing_required]
        assert "current_budget" not in required_fields

    def test_no_election_skips_candidate_bios_check(self):
        state = _make_minimal_state()
        state.election.election_required = False
        analyze_missing_items(state)
        conditional_fields = [i.canonical_field for i in state.document_status.missing_conditional]
        assert "candidate_bios" not in conditional_fields

    def test_election_required_triggers_candidate_bios_check(self):
        state = _make_minimal_state()
        state.election.election_required = True
        state.election.staggered_terms = False  # no seat map needed
        analyze_missing_items(state)
        conditional_fields = [i.canonical_field for i in state.document_status.missing_conditional]
        assert "candidate_bios" in conditional_fields

    def test_staggered_terms_without_seat_map_is_blocker(self):
        state = _make_minimal_state()
        state.election.election_required = True
        state.election.staggered_terms = True
        analyze_missing_items(state)
        blocker_fields = [i.canonical_field for i in state.document_status.missing_required
                          if i.severity == MissingItemSeverity.BLOCKER]
        assert "seat_map" in blocker_fields or "governing_document" in blocker_fields

    def test_staggered_terms_with_seat_map_resolves_blocker(self):
        from backend.app.models.packet import BoardSeat
        state = _make_minimal_state()
        state.election.election_required = True
        state.election.staggered_terms = True
        state.election.seat_map = [
            BoardSeat(seat_label="Seat A", current_occupant="Alice Smith", up_for_election=True)
        ]
        analyze_missing_items(state)
        blocker_fields = [i.canonical_field for i in state.document_status.missing_required
                          if i.severity == MissingItemSeverity.BLOCKER and i.canonical_field == "seat_map"]
        assert len(blocker_fields) == 0

    def test_manual_entry_can_resolve_meeting_date(self):
        state = _make_minimal_state()
        state.manual_entries["meeting_date"] = "2026-03-17"
        analyze_missing_items(state)
        required_fields = [i.canonical_field for i in state.document_status.missing_required]
        assert "meeting_date" not in required_fields

    def test_recommend_reserve_study_when_missing(self):
        state = _make_minimal_state()
        analyze_missing_items(state)
        rec_fields = [i.canonical_field for i in state.document_status.recommended_missing]
        assert "reserve_study" in rec_fields

    def test_prior_minutes_uploaded_resolves_conditional(self):
        state = _make_minimal_state()
        _add_doc(state, DocumentType.PRIOR_ANNUAL_MINUTES)
        analyze_missing_items(state)
        conditional_fields = [i.canonical_field for i in state.document_status.missing_conditional]
        assert "prior_annual_minutes" not in conditional_fields

    def test_summary_not_ready_with_blockers(self):
        state = _make_minimal_state()
        analyze_missing_items(state)
        summary = summarize_missing(state)
        assert not summary["ready_to_generate"]
        assert summary["blocker_count"] > 0

    def test_summary_ready_when_all_required_present(self):
        """A fully populated state should report ready to generate."""
        from backend.app.models.packet import BoardSeat
        state = _make_minimal_state()
        _add_doc(state, DocumentType.BYLAWS)
        _add_doc(state, DocumentType.CURRENT_BUDGET)
        _add_doc(state, DocumentType.PRIOR_YEAR_END_FINANCIALS)
        _add_doc(state, DocumentType.BOARD_ROSTER)
        state.meeting.meeting_date = date(2026, 3, 17)
        state.meeting.meeting_time = "6:00 PM"
        state.meeting.meeting_location = "Community Room"
        state.meeting.notice_date = date(2026, 2, 27)
        state.election.election_required = False
        analyze_missing_items(state)
        summary = summarize_missing(state)
        assert summary["ready_to_generate"], f"Should be ready. Still required: {summary['required']}"
