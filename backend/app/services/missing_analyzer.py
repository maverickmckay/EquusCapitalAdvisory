"""
Missing-items analysis engine.

Inspects a ProjectState and returns a DocumentStatus with categorized
lists of required, conditional, and recommended missing items.

Each MissingItem explains:
  - what is missing
  - why it matters
  - what document types would satisfy it
  - whether manual entry is an option
  - what risk exists if omitted
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from ..models.document import DocumentType
from ..models.packet import (
    MissingItem,
    MissingItemSeverity,
    DocumentStatus,
    ProjectState,
)

if TYPE_CHECKING:
    pass


def _has_doc_type(state: ProjectState, *doc_types: DocumentType) -> bool:
    """Return True if the project has at least one uploaded doc of any given type."""
    uploaded_types = {d.document_type for d in state.document_status.uploaded_docs}
    return any(dt in uploaded_types for dt in doc_types)


def _rule_val(state: ProjectState, field: str) -> Optional[Any]:
    return state.extracted_rules.get(field) or state.manual_entries.get(field)


def _manual(state: ProjectState, field: str) -> bool:
    return field in state.manual_entries and state.manual_entries[field] is not None


# ---------------------------------------------------------------------------
# Always-required items
# ---------------------------------------------------------------------------

def _check_governing_document(state: ProjectState) -> Optional[MissingItem]:
    has_gov = _has_doc_type(
        state,
        DocumentType.BYLAWS,
        DocumentType.DECLARATION,
        DocumentType.ARTICLES_OF_INCORPORATION,
    )
    if not has_gov:
        return MissingItem(
            severity=MissingItemSeverity.BLOCKER,
            canonical_field="governing_document",
            display_name="Governing Document (Bylaws or Declaration)",
            description="No bylaws, declaration, or articles of incorporation have been uploaded.",
            why_it_matters=(
                "The governing documents define meeting notice requirements, quorum thresholds, "
                "election procedures, proxy rules, and financial reporting obligations. "
                "Without them, the system cannot generate a legally reliable packet."
            ),
            satisfying_document_types=[DocumentType.BYLAWS, DocumentType.DECLARATION, DocumentType.ARTICLES_OF_INCORPORATION],
            manual_entry_possible=False,
            omission_risk="CRITICAL: Packet cannot be generated with reliable legal grounding.",
        )
    return None


def _check_meeting_date(state: ProjectState) -> Optional[MissingItem]:
    if state.meeting.meeting_date or _manual(state, "meeting_date"):
        return None
    return MissingItem(
        severity=MissingItemSeverity.BLOCKER,
        canonical_field="meeting_date",
        display_name="Annual Meeting Date",
        description="The date of the annual meeting has not been provided.",
        why_it_matters="Required for the notice, agenda, proxy form, and notice-period compliance calculation.",
        satisfying_document_types=[DocumentType.MEETING_LOGISTICS],
        manual_entry_possible=True,
        manual_entry_field="meeting.meeting_date",
        omission_risk="Notice and proxy forms cannot be generated without a meeting date.",
    )


def _check_meeting_time(state: ProjectState) -> Optional[MissingItem]:
    if state.meeting.meeting_time or _manual(state, "meeting_time"):
        return None
    return MissingItem(
        severity=MissingItemSeverity.REQUIRED,
        canonical_field="meeting_time",
        display_name="Annual Meeting Time",
        description="Meeting start time has not been provided.",
        why_it_matters="Required for all meeting notices and proxy forms.",
        satisfying_document_types=[DocumentType.MEETING_LOGISTICS],
        manual_entry_possible=True,
        manual_entry_field="meeting.meeting_time",
        omission_risk="Notice will be incomplete without a time.",
    )


def _check_meeting_location(state: ProjectState) -> Optional[MissingItem]:
    if state.meeting.meeting_location or _manual(state, "meeting_location"):
        return None
    return MissingItem(
        severity=MissingItemSeverity.REQUIRED,
        canonical_field="meeting_location",
        display_name="Annual Meeting Location / Address",
        description="No meeting location or address has been provided.",
        why_it_matters="Required on the formal notice. Owners need to know where to go.",
        satisfying_document_types=[DocumentType.MEETING_LOGISTICS],
        manual_entry_possible=True,
        manual_entry_field="meeting.meeting_location",
        omission_risk="Notice will be legally deficient if location is omitted.",
    )


def _check_board_roster(state: ProjectState) -> Optional[MissingItem]:
    has_roster = (
        _has_doc_type(state, DocumentType.BOARD_ROSTER, DocumentType.OFFICER_ROSTER)
        or state.election.board_roster
        or _manual(state, "board_roster")
    )
    if has_roster:
        return None
    return MissingItem(
        severity=MissingItemSeverity.REQUIRED,
        canonical_field="board_roster",
        display_name="Current Board Roster",
        description="No board roster or list of current directors has been uploaded or entered.",
        why_it_matters=(
            "Needed to identify incumbents, officers, expiring terms, and who is running for re-election. "
            "Also needed for the packet cover and organizational-meeting section."
        ),
        satisfying_document_types=[DocumentType.BOARD_ROSTER, DocumentType.OFFICER_ROSTER],
        manual_entry_possible=True,
        manual_entry_field="election.board_roster",
        omission_risk="Election section and cover page will be incomplete.",
    )


def _check_current_budget(state: ProjectState) -> Optional[MissingItem]:
    has_budget = (
        _has_doc_type(state, DocumentType.CURRENT_BUDGET)
        or state.financial.approved_budget_total is not None
        or _manual(state, "approved_budget_total")
    )
    if has_budget:
        return None
    return MissingItem(
        severity=MissingItemSeverity.REQUIRED,
        canonical_field="current_budget",
        display_name="Current Approved Budget",
        description="No approved operating budget for the current year has been uploaded.",
        why_it_matters=(
            "Many governing documents and state laws require the board to present the approved budget "
            "to owners at or before the annual meeting. Required for the financial summary section."
        ),
        satisfying_document_types=[DocumentType.CURRENT_BUDGET],
        manual_entry_possible=True,
        manual_entry_field="financial.approved_budget_total",
        omission_risk="Financial summary section will be incomplete or omitted.",
    )


def _check_financial_report(state: ProjectState) -> Optional[MissingItem]:
    has_financials = _has_doc_type(
        state,
        DocumentType.PRIOR_YEAR_END_FINANCIALS,
        DocumentType.AUDIT_REPORT,
        DocumentType.YTD_FINANCIALS,
    )
    if has_financials or state.financial.prior_year_end_net is not None:
        return None
    return MissingItem(
        severity=MissingItemSeverity.REQUIRED,
        canonical_field="financial_report",
        display_name="Prior Year-End Financial Statement or Annual Report",
        description="No prior year-end financial statement, audit, or review report has been uploaded.",
        why_it_matters=(
            "Bylaws and state condo/HOA statutes commonly require the association to furnish owners "
            "with an annual accounting or financial report at or before the annual meeting."
        ),
        satisfying_document_types=[
            DocumentType.PRIOR_YEAR_END_FINANCIALS,
            DocumentType.AUDIT_REPORT,
            DocumentType.YTD_FINANCIALS,
        ],
        manual_entry_possible=True,
        manual_entry_field="financial.prior_year_end_net",
        omission_risk="Compliance with financial-reporting obligation cannot be verified.",
    )


def _check_election_determination(state: ProjectState) -> Optional[MissingItem]:
    if state.election.election_required is not None or _manual(state, "election_required"):
        return None
    return MissingItem(
        severity=MissingItemSeverity.REQUIRED,
        canonical_field="election_required",
        display_name="Election Determination (seats up this year?)",
        description="It is not known whether any board seats are up for election this year.",
        why_it_matters=(
            "If an election is required, the packet must include proxy, nomination form, "
            "candidate bio section, and election explanation. If not, those sections may be omitted."
        ),
        satisfying_document_types=[DocumentType.BOARD_ROSTER],
        manual_entry_possible=True,
        manual_entry_field="election.election_required",
        omission_risk="Incorrect sections may be included or omitted from the packet.",
    )


# ---------------------------------------------------------------------------
# Conditionally required items
# ---------------------------------------------------------------------------

def _check_candidate_bios(state: ProjectState) -> Optional[MissingItem]:
    if not state.election.election_required:
        return None
    if state.election.candidate_bios or _manual(state, "candidate_bios"):
        return None
    return MissingItem(
        severity=MissingItemSeverity.CONDITIONAL,
        canonical_field="candidate_bios",
        display_name="Candidate Biographical Sketches",
        description="An election is scheduled but no candidate bios have been uploaded or entered.",
        why_it_matters=(
            "Candidate bio forms allow owners to make informed election choices. "
            "Many associations include them as a standard packet component."
        ),
        satisfying_document_types=[DocumentType.CANDIDATE_LIST, DocumentType.NOMINATION_FORM],
        manual_entry_possible=True,
        manual_entry_field="election.candidate_bios",
        omission_risk="Packet will include blank nomination form but no candidate profiles.",
        triggered_by="election_required=True",
    )


def _check_seat_map(state: ProjectState) -> Optional[MissingItem]:
    if not state.election.election_required:
        return None
    has_seat_map = bool(state.election.seat_map) or _manual(state, "seat_map")
    board_has_expiry = any(m.seat_up_this_year for m in state.election.board_roster)
    if has_seat_map or board_has_expiry:
        return None
    return MissingItem(
        severity=MissingItemSeverity.BLOCKER,
        canonical_field="seat_map",
        display_name="Board Seat / Term Expiration Map",
        description=(
            "Bylaws indicate staggered director terms, but no term-expiration data has been provided. "
            "It is unclear which seats expire this year."
        ),
        why_it_matters=(
            "Without a seat map, the election section cannot identify which positions are on the ballot. "
            "Electing wrong or extra directors violates the bylaws."
        ),
        satisfying_document_types=[DocumentType.BOARD_ROSTER],
        manual_entry_possible=True,
        manual_entry_field="election.seat_map",
        omission_risk="BLOCKER: Election section cannot be accurately generated.",
        triggered_by="staggered_terms=True AND election_required=True",
    )


def _check_prior_minutes(state: ProjectState) -> Optional[MissingItem]:
    has_minutes = _has_doc_type(state, DocumentType.PRIOR_ANNUAL_MINUTES)
    if has_minutes or _manual(state, "prior_minutes_status"):
        return None
    return MissingItem(
        severity=MissingItemSeverity.CONDITIONAL,
        canonical_field="prior_annual_minutes",
        display_name="Prior Annual Meeting Minutes",
        description="Prior year's annual meeting minutes have not been uploaded.",
        why_it_matters=(
            "Approval of prior meeting minutes is a standard annual meeting agenda item. "
            "If minutes are unavailable, the packet must include a records-transition explanation for the chair."
        ),
        satisfying_document_types=[DocumentType.PRIOR_ANNUAL_MINUTES],
        manual_entry_possible=True,
        manual_entry_field="prior_minutes_status",
        omission_risk="Packet will include placeholder; chair should be prepared to address.",
        triggered_by="annual_meeting_required=True",
    )


def _check_notice_date(state: ProjectState) -> Optional[MissingItem]:
    if state.meeting.notice_date or _manual(state, "notice_date"):
        return None
    if not state.meeting.meeting_date:
        return None  # meeting date blocker already covers this
    return MissingItem(
        severity=MissingItemSeverity.REQUIRED,
        canonical_field="notice_date",
        display_name="Notice Date (date notice will be sent)",
        description="The date the meeting notice will be (or was) mailed/delivered has not been confirmed.",
        why_it_matters=(
            "Notice-period compliance is calculated based on the days between notice date and meeting date. "
            "Required to confirm the notice satisfies the bylaw and state-law minimum."
        ),
        satisfying_document_types=[DocumentType.PRIOR_ANNUAL_NOTICE],
        manual_entry_possible=True,
        manual_entry_field="meeting.notice_date",
        omission_risk="Notice-period compliance cannot be validated.",
    )


def _check_special_assessment(state: ProjectState) -> Optional[MissingItem]:
    if _manual(state, "special_assessment_vote") and state.manual_entries.get("special_assessment_vote"):
        if not _manual(state, "special_assessment_text"):
            return MissingItem(
                severity=MissingItemSeverity.CONDITIONAL,
                canonical_field="special_assessment_text",
                display_name="Special Assessment Description and Amount",
                description="A special assessment vote is on the agenda but no description or amount has been entered.",
                why_it_matters="The notice and agenda must describe the special assessment with sufficient detail for owners to understand what they are voting on.",
                satisfying_document_types=[DocumentType.BOARD_RESOLUTION],
                manual_entry_possible=True,
                manual_entry_field="special_assessment_text",
                omission_risk="Inadequate notice of special assessment may be legally defective.",
                triggered_by="special_assessment_vote=True",
            )
    return None


def _check_amendment_text(state: ProjectState) -> Optional[MissingItem]:
    if _manual(state, "bylaw_amendment_vote") and state.manual_entries.get("bylaw_amendment_vote"):
        if not _has_doc_type(state, DocumentType.AMENDMENT) and not _manual(state, "amendment_text"):
            return MissingItem(
                severity=MissingItemSeverity.CONDITIONAL,
                canonical_field="amendment_text",
                display_name="Proposed Amendment Text",
                description="A bylaw or declaration amendment vote is scheduled but no amendment text has been provided.",
                why_it_matters="Owners must receive the full text of proposed amendments before the vote. Required by most state statutes and bylaws.",
                satisfying_document_types=[DocumentType.AMENDMENT],
                manual_entry_possible=True,
                manual_entry_field="amendment_text",
                omission_risk="Amendment vote may be legally invalid without proper notice of text.",
                triggered_by="bylaw_amendment_vote=True",
            )
    return None


# ---------------------------------------------------------------------------
# Recommended items
# ---------------------------------------------------------------------------

def _check_reserve_study(state: ProjectState) -> Optional[MissingItem]:
    if _has_doc_type(state, DocumentType.RESERVE_STUDY) or state.financial.reserve_fund_balance is not None:
        return None
    return MissingItem(
        severity=MissingItemSeverity.RECOMMENDED,
        canonical_field="reserve_study",
        display_name="Reserve Study Summary",
        description="No reserve study or reserve fund summary has been uploaded.",
        why_it_matters="Owners benefit from knowing the status of reserve funding. Some state statutes require reserve study disclosure.",
        satisfying_document_types=[DocumentType.RESERVE_STUDY],
        manual_entry_possible=True,
        manual_entry_field="financial.reserve_fund_balance",
        omission_risk="Reserve funding status will be omitted from financial summary.",
    )


def _check_prior_packet(state: ProjectState) -> Optional[MissingItem]:
    if _has_doc_type(state, DocumentType.PRIOR_ANNUAL_PACKET):
        return None
    return MissingItem(
        severity=MissingItemSeverity.RECOMMENDED,
        canonical_field="prior_packet",
        display_name="Prior Year Annual Meeting Packet",
        description="Last year's meeting packet has not been uploaded.",
        why_it_matters="Useful for style continuity, understanding prior agenda structure, and confirming what was last year's notice format.",
        satisfying_document_types=[DocumentType.PRIOR_ANNUAL_PACKET],
        manual_entry_possible=False,
        omission_risk="Style and continuity improvements may be missed.",
    )


def _check_owner_list(state: ProjectState) -> Optional[MissingItem]:
    if _has_doc_type(state, DocumentType.OWNER_MAILING_LIST):
        return None
    return MissingItem(
        severity=MissingItemSeverity.RECOMMENDED,
        canonical_field="owner_list",
        display_name="Owner Mailing List / Unit Roster",
        description="No owner mailing list has been uploaded.",
        why_it_matters="Required to prepare mailing labels and confirm unit count for quorum calculation.",
        satisfying_document_types=[DocumentType.OWNER_MAILING_LIST],
        manual_entry_possible=True,
        manual_entry_field="association.unit_count",
        omission_risk="Unit count may be uncertain; quorum threshold may need manual confirmation.",
    )


# ---------------------------------------------------------------------------
# Main analysis entry point
# ---------------------------------------------------------------------------

_REQUIRED_CHECKS = [
    _check_governing_document,
    _check_meeting_date,
    _check_meeting_time,
    _check_meeting_location,
    _check_board_roster,
    _check_current_budget,
    _check_financial_report,
    _check_election_determination,
    _check_notice_date,
]

_CONDITIONAL_CHECKS = [
    _check_candidate_bios,
    _check_seat_map,
    _check_prior_minutes,
    _check_special_assessment,
    _check_amendment_text,
]

_RECOMMENDED_CHECKS = [
    _check_reserve_study,
    _check_prior_packet,
    _check_owner_list,
]


def analyze_missing_items(state: ProjectState) -> DocumentStatus:
    """
    Run all missing-item checks against a ProjectState.

    Returns an updated DocumentStatus with the full analysis.
    Preserves previously-uploaded document metadata and any
    already-resolved items.
    """
    ds = state.document_status

    # Run required checks
    new_required: List[MissingItem] = []
    for check in _REQUIRED_CHECKS:
        item = check(state)
        if item:
            # Preserve existing resolution if already resolved
            existing = next((i for i in ds.missing_required if i.canonical_field == item.canonical_field), None)
            if existing and existing.resolved:
                item.resolved = True
                item.resolved_by = existing.resolved_by
                item.resolved_value = existing.resolved_value
            new_required.append(item)
    ds.missing_required = new_required

    # Run conditional checks
    new_conditional: List[MissingItem] = []
    for check in _CONDITIONAL_CHECKS:
        item = check(state)
        if item:
            existing = next((i for i in ds.missing_conditional if i.canonical_field == item.canonical_field), None)
            if existing and existing.resolved:
                item.resolved = True
                item.resolved_by = existing.resolved_by
                item.resolved_value = existing.resolved_value
            new_conditional.append(item)
    ds.missing_conditional = new_conditional

    # Run recommended checks
    new_recommended: List[MissingItem] = []
    for check in _RECOMMENDED_CHECKS:
        item = check(state)
        if item:
            new_recommended.append(item)
    ds.recommended_missing = new_recommended

    return ds


def summarize_missing(state: ProjectState) -> Dict[str, Any]:
    """Return a plain-English summary dict suitable for the dashboard."""
    ds = state.document_status
    blockers = [i for i in ds.missing_required if i.severity == MissingItemSeverity.BLOCKER and not i.resolved]
    required = [i for i in ds.missing_required if i.severity == MissingItemSeverity.REQUIRED and not i.resolved]
    conditional = [i for i in ds.missing_conditional if not i.resolved]
    recommended = [i for i in ds.recommended_missing if not i.resolved]

    return {
        "ready_to_generate": len(blockers) == 0 and len(required) == 0,
        "blocker_count": len(blockers),
        "required_count": len(required),
        "conditional_count": len(conditional),
        "recommended_count": len(recommended),
        "blockers": [{"field": i.canonical_field, "name": i.display_name, "description": i.description} for i in blockers],
        "required": [{"field": i.canonical_field, "name": i.display_name, "description": i.description} for i in required],
        "conditional": [{"field": i.canonical_field, "name": i.display_name, "description": i.description} for i in conditional],
        "recommended": [{"field": i.canonical_field, "name": i.display_name, "description": i.description} for i in recommended],
    }
