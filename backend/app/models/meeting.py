from __future__ import annotations
from enum import Enum
from typing import Optional, List
from datetime import date, time
from pydantic import BaseModel, Field


class MeetingType(str, Enum):
    ANNUAL = "annual"
    SPECIAL = "special"
    ORGANIZATIONAL = "organizational"


class QuorumBasis(str, Enum):
    PERCENTAGE_OF_UNITS = "percentage_of_units"
    PERCENTAGE_OF_VOTES = "percentage_of_votes"
    PERCENTAGE_OF_TOTAL_MEMBERSHIP = "percentage_of_total_membership"
    FIXED_NUMBER = "fixed_number"
    MAJORITY_OF_BOARD = "majority_of_board"


class NoticeMethod(str, Enum):
    US_MAIL = "us_mail"
    EMAIL = "email"
    HAND_DELIVERY = "hand_delivery"
    POSTED = "posted"
    ANY_OF_ABOVE = "any_of_above"
    MAIL_OR_EMAIL = "mail_or_email"


class AgendaItem(BaseModel):
    order: int
    title: str
    description: Optional[str] = None
    requires_vote: bool = False
    vote_threshold: Optional[str] = None
    notes: Optional[str] = None


class MeetingProfile(BaseModel):
    meeting_type: MeetingType = MeetingType.ANNUAL
    meeting_date: Optional[date] = None
    meeting_time: Optional[str] = None
    registration_time: Optional[str] = None
    meeting_location: Optional[str] = None
    meeting_address: Optional[str] = None
    virtual_option: bool = False
    virtual_link: Optional[str] = None

    # Notice
    notice_date: Optional[date] = None
    notice_method: NoticeMethod = NoticeMethod.US_MAIL
    notice_period_min_days: Optional[int] = None
    notice_period_max_days: Optional[int] = None

    # Quorum
    quorum_threshold: Optional[float] = None
    quorum_basis: QuorumBasis = QuorumBasis.PERCENTAGE_OF_VOTES
    quorum_threshold_raw: Optional[str] = None
    adjournment_rules: Optional[str] = None
    adjourned_meeting_quorum: Optional[str] = None

    # Proxy
    proxy_permitted: bool = True
    proxy_deadline: Optional[date] = None
    proxy_revocable: bool = True
    proxy_valid_for_single_meeting: bool = True
    proxy_notes: Optional[str] = None
    absentee_ballot_permitted: bool = False
    electronic_voting_permitted: bool = False

    # Agenda
    agenda_items: List[AgendaItem] = Field(default_factory=list)
    special_agenda_items: List[str] = Field(default_factory=list)

    # Action thresholds
    action_majority_threshold: Optional[str] = None
    supermajority_threshold: Optional[str] = None

    class Config:
        use_enum_values = True
