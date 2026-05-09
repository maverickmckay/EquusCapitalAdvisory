"""
Project management API routes.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..models.association import AssociationProfile
from ..models.packet import ProjectState, MeetingProfile, FinancialProfile, ElectionProfile
from ..services.project_store import save_project, load_project, list_projects, delete_project
from ..services.jurisdiction_loader import load_jurisdiction, list_available_jurisdictions
from ..services.missing_analyzer import analyze_missing_items, summarize_missing
from ..services.validator import run_validation, validation_summary

router = APIRouter(prefix="/api/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    association_name: str
    state: str
    association_type: str = "condominium"
    meeting_year: int
    unit_count: Optional[int] = None
    management_company: Optional[str] = None
    management_contact: Optional[str] = None
    management_email: Optional[str] = None
    management_phone: Optional[str] = None


class UpdateMeetingRequest(BaseModel):
    meeting_date: Optional[str] = None
    meeting_time: Optional[str] = None
    registration_time: Optional[str] = None
    meeting_location: Optional[str] = None
    meeting_address: Optional[str] = None
    notice_date: Optional[str] = None
    quorum_threshold: Optional[float] = None
    proxy_permitted: Optional[bool] = None
    proxy_deadline: Optional[str] = None
    virtual_option: Optional[bool] = None
    virtual_link: Optional[str] = None


class UpdateFinancialRequest(BaseModel):
    approved_budget_total: Optional[float] = None
    approved_budget_year: Optional[int] = None
    approved_budget_notes: Optional[str] = None
    prior_budget_total: Optional[float] = None
    prior_year_end_income: Optional[float] = None
    prior_year_end_expenses: Optional[float] = None
    prior_year_end_net: Optional[float] = None
    ytd_income: Optional[float] = None
    ytd_expenses: Optional[float] = None
    reserve_fund_balance: Optional[float] = None
    reserve_percent_funded: Optional[float] = None
    reserve_study_year: Optional[int] = None
    audit_completed: Optional[bool] = None
    audit_year: Optional[int] = None


class UpdateElectionRequest(BaseModel):
    election_required: Optional[bool] = None
    election_reason: Optional[str] = None
    board_size: Optional[int] = None
    seats_up_count: Optional[int] = None
    director_term_length_years: Optional[int] = None
    staggered_terms: Optional[bool] = None
    nomination_from_floor: Optional[bool] = None
    ballot_required: Optional[bool] = None
    election_notes: Optional[str] = None


class ManualEntryRequest(BaseModel):
    entries: Dict[str, Any]


@router.get("")
def list_all_projects():
    return {"projects": list_projects()}


@router.get("/jurisdictions")
def get_jurisdictions():
    available = list_available_jurisdictions()
    return {"jurisdictions": available}


@router.post("")
def create_project(req: CreateProjectRequest):
    from ..models.association import AssociationProfile, AssociationType
    from datetime import date

    try:
        assoc_type = AssociationType(req.association_type)
    except ValueError:
        assoc_type = AssociationType.CONDOMINIUM

    assoc = AssociationProfile(
        association_name=req.association_name,
        state=req.state.upper(),
        association_type=assoc_type,
        meeting_year=req.meeting_year,
        unit_count=req.unit_count,
        management_company=req.management_company,
        management_contact=req.management_contact,
        management_email=req.management_email,
        management_phone=req.management_phone,
    )

    state = ProjectState(
        project_name=f"{req.association_name} — {req.meeting_year} Annual Meeting",
        association=assoc,
    )

    # Load jurisdiction rules
    state.jurisdiction_rules = load_jurisdiction(req.state)

    # Run initial analysis
    state.document_status = analyze_missing_items(state)

    save_project(state)
    return {"project_id": state.project_id, "project_name": state.project_name}


@router.get("/{project_id}")
def get_project(project_id: str):
    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")
    return state.dict()


@router.delete("/{project_id}")
def remove_project(project_id: str):
    ok = delete_project(project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"deleted": project_id}


@router.put("/{project_id}/meeting")
def update_meeting(project_id: str, req: UpdateMeetingRequest):
    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    from datetime import date as date_type
    import datetime as dt_module

    def parse_date(s):
        if s is None:
            return None
        try:
            return dt_module.date.fromisoformat(s)
        except Exception:
            return None

    meeting = state.meeting
    if req.meeting_date is not None:
        meeting.meeting_date = parse_date(req.meeting_date)
    if req.meeting_time is not None:
        meeting.meeting_time = req.meeting_time
    if req.registration_time is not None:
        meeting.registration_time = req.registration_time
    if req.meeting_location is not None:
        meeting.meeting_location = req.meeting_location
    if req.meeting_address is not None:
        meeting.meeting_address = req.meeting_address
    if req.notice_date is not None:
        meeting.notice_date = parse_date(req.notice_date)
    if req.quorum_threshold is not None:
        meeting.quorum_threshold = req.quorum_threshold
    if req.proxy_permitted is not None:
        meeting.proxy_permitted = req.proxy_permitted
    if req.proxy_deadline is not None:
        meeting.proxy_deadline = parse_date(req.proxy_deadline)
    if req.virtual_option is not None:
        meeting.virtual_option = req.virtual_option
    if req.virtual_link is not None:
        meeting.virtual_link = req.virtual_link

    state.meeting = meeting
    state.document_status = analyze_missing_items(state)
    save_project(state)
    return {"ok": True}


@router.put("/{project_id}/financial")
def update_financial(project_id: str, req: UpdateFinancialRequest):
    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    fin = state.financial
    for field, val in req.dict(exclude_none=True).items():
        setattr(fin, field, val)
    state.financial = fin
    state.document_status = analyze_missing_items(state)
    save_project(state)
    return {"ok": True}


@router.put("/{project_id}/election")
def update_election(project_id: str, req: UpdateElectionRequest):
    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    elec = state.election
    for field, val in req.dict(exclude_none=True).items():
        setattr(elec, field, val)
    state.election = elec
    state.document_status = analyze_missing_items(state)
    save_project(state)
    return {"ok": True}


@router.post("/{project_id}/manual_entries")
def update_manual_entries(project_id: str, req: ManualEntryRequest):
    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    state.manual_entries.update(req.entries)
    state.document_status = analyze_missing_items(state)
    save_project(state)
    return {"ok": True, "entries_updated": list(req.entries.keys())}


@router.get("/{project_id}/missing_items")
def get_missing_items(project_id: str):
    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    state.document_status = analyze_missing_items(state)
    save_project(state)
    return {
        "summary": summarize_missing(state),
        "required": [i.dict() for i in state.document_status.missing_required],
        "conditional": [i.dict() for i in state.document_status.missing_conditional],
        "recommended": [i.dict() for i in state.document_status.recommended_missing],
    }


@router.get("/{project_id}/validation")
def get_validation(project_id: str):
    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    results = run_validation(state)
    return {
        "summary": validation_summary(results),
        "results": [r.dict() for r in results],
    }


@router.put("/{project_id}/packet_sections")
def update_packet_sections(project_id: str, sections: Dict[str, bool]):
    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    ps = state.packet_sections
    for field, val in sections.items():
        if hasattr(ps, field):
            setattr(ps, field, val)
    state.packet_sections = ps
    save_project(state)
    return {"ok": True}
