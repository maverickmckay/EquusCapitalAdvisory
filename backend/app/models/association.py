from __future__ import annotations
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class AssociationType(str, Enum):
    HOA = "hoa"
    CONDOMINIUM = "condominium"
    COOPERATIVE = "cooperative"
    TOWNHOME = "townhome"
    MASTER = "master"
    OTHER = "other"


class VoteStructure(str, Enum):
    ONE_VOTE_PER_UNIT = "one_vote_per_unit"
    WEIGHTED_BY_PERCENTAGE = "weighted_by_percentage"
    WEIGHTED_BY_SQUARE_FOOTAGE = "weighted_by_square_footage"
    WEIGHTED_BY_VALUE = "weighted_by_value"
    OTHER = "other"


class GovDocPriority(str, Enum):
    """Which document controls when governing documents conflict."""
    DECLARATION_OVER_BYLAWS = "declaration_over_bylaws"
    BYLAWS_OVER_DECLARATION = "bylaws_over_declaration"
    STATE_LAW_FIRST = "state_law_first"
    DECLARATION_BYLAWS_RULES = "declaration_bylaws_rules"


class AssociationProfile(BaseModel):
    association_name: str = Field(..., description="Legal name of the association")
    state: str = Field(..., description="Two-letter US state code, e.g. WI")
    association_type: AssociationType = Field(AssociationType.CONDOMINIUM)
    fiscal_year_end_month: int = Field(12, ge=1, le=12, description="Month fiscal year ends (1-12)")
    unit_count: Optional[int] = Field(None, ge=1, description="Total number of units/lots")
    vote_structure: VoteStructure = Field(VoteStructure.ONE_VOTE_PER_UNIT)
    governing_doc_priority: GovDocPriority = Field(GovDocPriority.DECLARATION_OVER_BYLAWS)
    management_company: Optional[str] = None
    management_contact: Optional[str] = None
    management_email: Optional[str] = None
    management_phone: Optional[str] = None
    registered_agent: Optional[str] = None
    principal_office_address: Optional[str] = None
    meeting_year: int = Field(..., description="Calendar year of this annual meeting")

    class Config:
        use_enum_values = True
