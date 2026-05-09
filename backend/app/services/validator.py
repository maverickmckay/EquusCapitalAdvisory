"""
Compliance validation engine.

Runs a series of validation checks against the project state after
missing-item analysis has been completed. Produces ValidationResult
objects with PASS / WARNING / BLOCKER severity levels.

All thresholds are driven by extracted governing-document rules
overlaid with the active jurisdiction rules. Nothing is hardcoded
for a specific association.
"""
from __future__ import annotations
from datetime import date, timedelta
from typing import List, Optional, Any, TYPE_CHECKING

from ..models.packet import ValidationResult, ValidationSeverity, ProjectState

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pass(category: str, title: str, detail: str, source: str = "") -> ValidationResult:
    return ValidationResult(severity=ValidationSeverity.PASS, category=category, title=title, detail=detail, source_rule=source)


def _warn(category: str, title: str, detail: str, recommendation: str = "", source: str = "") -> ValidationResult:
    return ValidationResult(severity=ValidationSeverity.WARNING, category=category, title=title, detail=detail, recommendation=recommendation, source_rule=source)


def _block(category: str, title: str, detail: str, recommendation: str = "", source: str = "") -> ValidationResult:
    return ValidationResult(severity=ValidationSeverity.BLOCKER, category=category, title=title, detail=detail, recommendation=recommendation, source_rule=source, blocking=True)


def _info(category: str, title: str, detail: str) -> ValidationResult:
    return ValidationResult(severity=ValidationSeverity.INFO, category=category, title=title, detail=detail)


def _rule(state: ProjectState, field: str) -> Optional[Any]:
    """
    Look up a rule value from extracted rules or jurisdiction defaults.
    Extracted rules are stored as dicts; unwrap the 'value' key.
    """
    raw = state.extracted_rules.get(field)
    if raw is not None:
        if isinstance(raw, dict):
            return raw.get("value", raw)
        return raw
    return state.jurisdiction_rules.get(field)


# ---------------------------------------------------------------------------
# Individual validation checks
# ---------------------------------------------------------------------------

def validate_notice_period(state: ProjectState) -> Optional[ValidationResult]:
    if not state.meeting.meeting_date or not state.meeting.notice_date:
        return _warn(
            "Notice", "Notice Period Not Verifiable",
            "Meeting date or notice date is missing; notice period compliance cannot be validated.",
            "Enter both meeting date and notice date."
        )

    days_notice = (state.meeting.meeting_date - state.meeting.notice_date).days
    min_days = (
        state.meeting.notice_period_min_days
        or _rule(state, "notice_period_days")
        or state.jurisdiction_rules.get("default_notice_period_days")
        or 10
    )
    max_days = (
        state.meeting.notice_period_max_days
        or _rule(state, "notice_period_max_days")
        or state.jurisdiction_rules.get("default_notice_period_max_days")
    )

    source = "Bylaws / Jurisdiction Rules"

    if days_notice < min_days:
        return _block(
            "Notice",
            "Notice Period Too Short",
            f"Notice date is {days_notice} days before the meeting; minimum required is {min_days} days.",
            f"Move notice date to at least {state.meeting.meeting_date - timedelta(days=min_days)} or later the meeting date.",
            source,
        )
    if max_days and days_notice > max_days:
        return _warn(
            "Notice",
            "Notice Period May Exceed Maximum",
            f"Notice date is {days_notice} days before the meeting; governing documents may limit notice to {max_days} days.",
            "Confirm whether the governing documents impose a maximum notice window.",
            source,
        )
    return _pass(
        "Notice",
        "Notice Period Satisfied",
        f"Notice date is {days_notice} days before the meeting; minimum required is {min_days} days.",
        source,
    )


def validate_quorum(state: ProjectState) -> Optional[ValidationResult]:
    threshold = (
        state.meeting.quorum_threshold
        or _rule(state, "quorum_threshold_pct")
        or state.jurisdiction_rules.get("default_quorum_pct")
    )
    if threshold is None:
        return _warn(
            "Quorum",
            "Quorum Threshold Not Identified",
            "No quorum threshold was extracted from the governing documents.",
            "Manually enter the quorum threshold or confirm the governing-document provision.",
        )
    return _pass(
        "Quorum",
        "Quorum Threshold Identified",
        f"Quorum threshold: {threshold}% of eligible votes (in person or by proxy).",
        "Extracted from governing documents",
    )


def validate_election_consistency(state: ProjectState) -> Optional[ValidationResult]:
    if not state.election.election_required:
        return _info("Election", "No Election This Year", "No board election is scheduled for this meeting.")

    seat_map = state.election.seat_map
    board_roster = state.election.board_roster
    # Check election.staggered_terms directly as well as extracted rules
    staggered = (
        state.election.staggered_terms
        or (_rule(state, "staggered_terms") is True)
        or (isinstance(_rule(state, "staggered_terms"), dict) and _rule(state, "staggered_terms").get("value"))
    )

    if staggered and not seat_map and not any(m.seat_up_this_year for m in board_roster):
        return _block(
            "Election",
            "Staggered Terms — Expiring Seats Not Identified",
            "Governing documents indicate staggered director terms, but no seat expiration data has been provided. "
            "It is impossible to determine which seats are on the ballot this year.",
            "Upload the current board roster with term dates, or manually enter the seat map.",
            "Bylaws staggered-terms provision",
        )

    seat_count = (
        len([s for s in seat_map if s.up_for_election])
        if seat_map
        else len([m for m in board_roster if m.seat_up_this_year])
    )

    if seat_count == 0:
        return _warn(
            "Election",
            "Election Required but Zero Seats Identified",
            "An election is required but no seats have been flagged as up for election.",
            "Confirm which board seats expire this year.",
        )

    return _pass(
        "Election",
        f"Election Seats Identified: {seat_count} seat(s) on ballot",
        f"{seat_count} board seat(s) are up for election at this meeting.",
    )


def validate_proxy_language(state: ProjectState) -> Optional[ValidationResult]:
    proxy_permitted = (
        state.meeting.proxy_permitted
        if state.meeting.proxy_permitted is not None
        else _rule(state, "proxy_permitted")
    )
    jx_proxy_notes = state.jurisdiction_rules.get("proxy_notes")

    if proxy_permitted is False:
        return _info("Proxy", "Proxy Voting Not Permitted", "Governing documents do not appear to permit proxy voting.")

    if proxy_permitted is None:
        return _warn(
            "Proxy",
            "Proxy Permission Not Confirmed",
            "No explicit proxy provision was found in the governing documents.",
            "Confirm whether proxy voting is permitted; state default rules may apply.",
            jx_proxy_notes or "",
        )

    single_meeting = _rule(state, "proxy_single_meeting")
    note = "Proxy form is limited to this specific meeting." if single_meeting else "Confirm proxy scope in proxy form."
    return _pass("Proxy", "Proxy Voting Permitted", f"Proxy voting is permitted. {note}")


def validate_financial_section(state: ProjectState) -> Optional[ValidationResult]:
    annual_report_required = _rule(state, "annual_financial_report_required")
    has_budget = state.financial.approved_budget_total is not None
    has_financials = (
        state.financial.prior_year_end_net is not None
        or state.financial.ytd_income is not None
    )

    if annual_report_required and not has_financials:
        return _warn(
            "Financial",
            "Annual Financial Report Required by Governing Documents",
            "The governing documents require an annual financial report be furnished to owners, "
            "but no prior year-end financials have been provided.",
            "Upload the prior year-end financial statement or annual accountant's report.",
            "Governing documents — financial reporting obligation",
        )

    if not has_budget:
        return _warn(
            "Financial",
            "Current Budget Not Available",
            "No current approved budget has been provided for the financial summary section.",
            "Upload or enter the current year approved budget.",
        )

    return _pass(
        "Financial",
        "Financial Data Available",
        "Budget and/or financial data are present for the financial summary section.",
    )


def validate_meeting_metadata_complete(state: ProjectState) -> Optional[ValidationResult]:
    missing_fields = []
    if not state.meeting.meeting_date:
        missing_fields.append("meeting date")
    if not state.meeting.meeting_time:
        missing_fields.append("meeting time")
    if not state.meeting.meeting_location:
        missing_fields.append("meeting location")

    if missing_fields:
        return _block(
            "Meeting Metadata",
            "Critical Meeting Information Missing",
            f"The following required meeting details are missing: {', '.join(missing_fields)}.",
            "Enter all meeting logistics before generating the packet.",
        )
    return _pass(
        "Meeting Metadata",
        "Meeting Details Complete",
        f"Date, time, and location are all present.",
    )


def validate_board_roster_present(state: ProjectState) -> Optional[ValidationResult]:
    if not state.election.board_roster:
        return _warn(
            "Roster",
            "Board Roster Not Provided",
            "No board member records have been entered or parsed from uploaded documents.",
            "Upload the board roster or enter board member names manually.",
        )
    return _pass(
        "Roster",
        f"Board Roster Present ({len(state.election.board_roster)} member(s))",
        "Board member records are available for use in the packet.",
    )


def validate_unresolved_ambiguities(state: ProjectState) -> List[ValidationResult]:
    results = []
    for rule in state.extracted_rules.values():
        if isinstance(rule, dict) and rule.get("is_ambiguous") and not rule.get("confirmed_by_user"):
            results.append(_warn(
                "Ambiguity",
                f"Ambiguous Rule: {rule.get('display_name', rule.get('canonical_field', 'Unknown'))}",
                rule.get("ambiguity_note", "This extracted rule requires user confirmation."),
                "Review and confirm this rule in the Rule Review screen.",
            ))
    return results


def validate_org_meeting(state: ProjectState) -> Optional[ValidationResult]:
    org_required = _rule(state, "org_meeting_after_annual")
    if org_required:
        return _info(
            "Organizational Meeting",
            "Organizational Meeting Required After Annual Meeting",
            "Governing documents require an organizational meeting of the board immediately following the annual meeting. "
            "Ensure the agenda includes this item and that new officers are elected at that time.",
        )
    return None


# ---------------------------------------------------------------------------
# Main validation runner
# ---------------------------------------------------------------------------

_SINGLE_CHECKS = [
    validate_notice_period,
    validate_quorum,
    validate_election_consistency,
    validate_proxy_language,
    validate_financial_section,
    validate_meeting_metadata_complete,
    validate_board_roster_present,
    validate_org_meeting,
]


def run_validation(state: ProjectState) -> List[ValidationResult]:
    """
    Execute all validation checks and return a list of ValidationResult objects.
    BLOCKERs indicate the packet should not be generated.
    WARNINGs indicate the packet can be generated but has risks.
    PASSes confirm each rule is satisfied.
    """
    results: List[ValidationResult] = []

    for check in _SINGLE_CHECKS:
        try:
            result = check(state)
            if result:
                results.append(result)
        except Exception as e:
            results.append(_warn("System", f"Validation Check Error", str(e)))

    # Multi-result checks
    try:
        results.extend(validate_unresolved_ambiguities(state))
    except Exception:
        pass

    return results


def validation_summary(results: List[ValidationResult]) -> dict:
    blockers = [r for r in results if r.severity == ValidationSeverity.BLOCKER]
    warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
    passes = [r for r in results if r.severity == ValidationSeverity.PASS]
    infos = [r for r in results if r.severity == ValidationSeverity.INFO]
    return {
        "ready_to_generate": len(blockers) == 0,
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "pass_count": len(passes),
        "info_count": len(infos),
        "blockers": [{"title": r.title, "detail": r.detail} for r in blockers],
        "warnings": [{"title": r.title, "detail": r.detail} for r in warnings],
    }
