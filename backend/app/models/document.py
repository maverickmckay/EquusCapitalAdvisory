from __future__ import annotations
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class DocumentType(str, Enum):
    # Governing documents
    BYLAWS = "bylaws"
    DECLARATION = "declaration"
    ARTICLES_OF_INCORPORATION = "articles_of_incorporation"
    RULES_AND_REGULATIONS = "rules_and_regulations"
    ELECTION_RULES = "election_rules"
    BOARD_RESOLUTION = "board_resolution"
    AMENDMENT = "amendment"

    # Meeting history
    PRIOR_ANNUAL_PACKET = "prior_annual_packet"
    PRIOR_ANNUAL_NOTICE = "prior_annual_notice"
    PRIOR_AGENDA = "prior_agenda"
    PRIOR_PROXY = "prior_proxy"
    PRIOR_BALLOT = "prior_ballot"
    PRIOR_ANNUAL_MINUTES = "prior_annual_minutes"
    PRIOR_ORG_MEETING_MINUTES = "prior_org_meeting_minutes"

    # Financial
    CURRENT_BUDGET = "current_budget"
    PRIOR_BUDGET = "prior_budget"
    YTD_FINANCIALS = "ytd_financials"
    PRIOR_YEAR_END_FINANCIALS = "prior_year_end_financials"
    RESERVE_STUDY = "reserve_study"
    AUDIT_REPORT = "audit_report"
    DELINQUENCY_SUMMARY = "delinquency_summary"

    # Operational
    BOARD_ROSTER = "board_roster"
    OFFICER_ROSTER = "officer_roster"
    MANAGEMENT_CONTACT = "management_contact"
    OWNER_MAILING_LIST = "owner_mailing_list"
    CANDIDATE_LIST = "candidate_list"
    NOMINATION_FORM = "nomination_form"
    MEETING_LOGISTICS = "meeting_logistics"

    # Legal / jurisdiction
    JURISDICTION_RULES = "jurisdiction_rules"
    LEGAL_MEMO = "legal_memo"
    COMPLIANCE_CHECKLIST = "compliance_checklist"

    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIED = "unverified"


class ExtractedRule(BaseModel):
    """A single governance rule extracted from a document."""
    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    canonical_field: str = Field(..., description="Machine-readable rule name, e.g. 'notice_period_days'")
    display_name: str = Field(..., description="Human-readable rule name")
    value: Any = Field(..., description="Extracted value (int, str, bool, etc.)")
    raw_text: str = Field(..., description="Raw text excerpt from source document")
    source_document_id: str
    source_section: Optional[str] = None
    source_page: Optional[int] = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    is_ambiguous: bool = False
    ambiguity_note: Optional[str] = None
    confirmed_by_user: bool = False


class ParsedDocument(BaseModel):
    """Results of parsing an uploaded document."""
    document_id: str
    document_type: DocumentType
    full_text: str = ""
    extracted_rules: List[ExtractedRule] = Field(default_factory=list)
    extracted_facts: Dict[str, Any] = Field(default_factory=dict)
    parse_errors: List[str] = Field(default_factory=list)
    page_count: Optional[int] = None
    parsed_at: datetime = Field(default_factory=datetime.utcnow)


class UploadedDocument(BaseModel):
    """Metadata for a file uploaded to the project."""
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    original_filename: str
    document_type: DocumentType = DocumentType.UNKNOWN
    classification_confidence: ConfidenceLevel = ConfidenceLevel.UNVERIFIED
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    parsed: bool = False
    parse_error: Optional[str] = None
    user_confirmed_type: bool = False
    notes: Optional[str] = None

    class Config:
        use_enum_values = True
