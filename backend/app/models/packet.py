from __future__ import annotations
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field
import uuid

from .document import UploadedDocument, DocumentType
from .meeting import MeetingProfile
from .association import AssociationProfile


class MissingItemSeverity(str, Enum):
    BLOCKER = "blocker"
    REQUIRED = "required"
    CONDITIONAL = "conditional"
    RECOMMENDED = "recommended"


class ValidationSeverity(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    BLOCKER = "blocker"
    INFO = "info"


class MissingItem(BaseModel):
    """A single missing file or data point identified by the analysis engine."""
    item_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    severity: MissingItemSeverity
    canonical_field: str
    display_name: str
    description: str
    why_it_matters: str
    satisfying_document_types: List[DocumentType] = Field(default_factory=list)
    manual_entry_possible: bool = True
    manual_entry_field: Optional[str] = None
    omission_risk: Optional[str] = None
    triggered_by: Optional[str] = None
    resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_value: Optional[Any] = None

    class Config:
        use_enum_values = True


class ValidationResult(BaseModel):
    """One validation check result."""
    check_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    severity: ValidationSeverity
    category: str
    title: str
    detail: str
    recommendation: Optional[str] = None
    source_rule: Optional[str] = None
    blocking: bool = False

    class Config:
        use_enum_values = True


class DocumentStatus(BaseModel):
    """Summary of document upload and parsing status for a project."""
    uploaded_docs: List[UploadedDocument] = Field(default_factory=list)
    parsed_doc_ids: List[str] = Field(default_factory=list)
    missing_required: List[MissingItem] = Field(default_factory=list)
    missing_conditional: List[MissingItem] = Field(default_factory=list)
    recommended_missing: List[MissingItem] = Field(default_factory=list)
    ambiguity_flags: List[str] = Field(default_factory=list)
    validation_warnings: List[ValidationResult] = Field(default_factory=list)

    @property
    def has_blockers(self) -> bool:
        return any(i.severity == MissingItemSeverity.BLOCKER for i in self.missing_required)

    @property
    def unresolved_required(self) -> List[MissingItem]:
        return [i for i in self.missing_required if not i.resolved]

    @property
    def all_required_resolved(self) -> bool:
        return all(i.resolved for i in self.missing_required)


class BoardMember(BaseModel):
    name: str
    unit_number: Optional[str] = None
    title: Optional[str] = None
    term_start: Optional[date] = None
    term_end: Optional[date] = None
    term_length_years: Optional[int] = None
    is_officer: bool = False
    officer_title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    incumbent: bool = True
    seat_up_this_year: bool = False


class BoardSeat(BaseModel):
    """Represents one board seat and its election status."""
    seat_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    seat_label: str
    current_occupant: Optional[str] = None
    term_length_years: Optional[int] = None
    term_expiry_year: Optional[int] = None
    up_for_election: bool = False
    incumbent_running: Optional[bool] = None


class CandidateBio(BaseModel):
    name: str
    unit_number: Optional[str] = None
    bio_text: Optional[str] = None
    years_in_community: Optional[int] = None
    relevant_experience: Optional[str] = None
    why_running: Optional[str] = None
    incumbent: bool = False


class ElectionProfile(BaseModel):
    election_required: bool = False
    election_reason: Optional[str] = None
    board_size: Optional[int] = None
    board_roster: List[BoardMember] = Field(default_factory=list)
    officer_roster: List[BoardMember] = Field(default_factory=list)
    seat_map: List[BoardSeat] = Field(default_factory=list)
    incumbents_running: List[str] = Field(default_factory=list)
    nomination_deadline: Optional[date] = None
    nomination_from_floor: bool = True
    candidate_bios: List[CandidateBio] = Field(default_factory=list)
    ballot_required: bool = False
    proxy_allowed_for_election: bool = True
    election_notes: Optional[str] = None
    director_term_length_years: Optional[int] = None
    staggered_terms: bool = False
    seats_up_count: Optional[int] = None


class FinancialProfile(BaseModel):
    approved_budget_year: Optional[int] = None
    approved_budget_total: Optional[float] = None
    approved_budget_notes: Optional[str] = None
    prior_budget_total: Optional[float] = None
    prior_year_end_income: Optional[float] = None
    prior_year_end_expenses: Optional[float] = None
    prior_year_end_net: Optional[float] = None
    ytd_income: Optional[float] = None
    ytd_expenses: Optional[float] = None
    ytd_as_of_date: Optional[date] = None
    reserve_fund_balance: Optional[float] = None
    reserve_study_year: Optional[int] = None
    reserve_percent_funded: Optional[float] = None
    audit_completed: Optional[bool] = None
    audit_year: Optional[int] = None
    key_budget_line_items: Dict[str, float] = Field(default_factory=dict)
    key_financial_notes: List[str] = Field(default_factory=list)
    financial_source_docs: List[str] = Field(default_factory=list)


class PacketSections(BaseModel):
    """Flags controlling which sections are included in the packet."""
    cover_page: bool = True
    table_of_contents: bool = True
    notice: bool = True
    agenda: bool = True
    proxy: bool = True
    nomination_form: bool = False
    candidate_bios: bool = False
    financial_summary: bool = True
    budget_summary: bool = True
    prior_minutes_status: bool = True
    election_explanation: bool = False
    bylaw_excerpts: bool = False
    meeting_instructions: bool = True
    minutes_template: bool = True
    validation_appendix: bool = False
    custom_sections: List[str] = Field(default_factory=list)


class ProjectState(BaseModel):
    """The full runtime state of one HOA project."""
    project_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    association: Optional[AssociationProfile] = None
    meeting: MeetingProfile = Field(default_factory=MeetingProfile)
    financial: FinancialProfile = Field(default_factory=FinancialProfile)
    election: ElectionProfile = Field(default_factory=ElectionProfile)
    document_status: DocumentStatus = Field(default_factory=DocumentStatus)
    packet_sections: PacketSections = Field(default_factory=PacketSections)

    # Extracted governance rules from parsed documents
    extracted_rules: Dict[str, Any] = Field(default_factory=dict)

    # Jurisdiction overlay
    jurisdiction_rules: Dict[str, Any] = Field(default_factory=dict)

    # Generation output paths
    generated_tex_path: Optional[str] = None
    generated_pdf_path: Optional[str] = None
    last_generated_at: Optional[datetime] = None

    # User-supplied overrides for manual entry
    manual_entries: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True
