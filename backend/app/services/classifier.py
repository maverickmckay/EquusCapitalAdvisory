"""
Document classifier.

Uses keyword/phrase pattern matching to determine the most likely
DocumentType for an uploaded file.  Assigns a ConfidenceLevel and
allows user confirmation to override.
"""
from __future__ import annotations
import re
from typing import Tuple, List
from pathlib import Path

from ..models.document import DocumentType, ConfidenceLevel


# ---------------------------------------------------------------------------
# Signal definitions
# Each entry: (DocumentType, weight, list-of-regex-patterns)
# Higher weight = stronger signal; patterns are case-insensitive
# ---------------------------------------------------------------------------

_SIGNALS: List[Tuple[DocumentType, int, List[str]]] = [
    # Governing documents
    (DocumentType.BYLAWS, 10, [
        r"\bbylaws?\b",
        r"\bcode of regulations\b",
        r"officers? of the association",
        r"article\s+[ivxlcdm]+\s+[-–]\s+meetings",
    ]),
    (DocumentType.DECLARATION, 10, [
        r"\bdeclaration of condominium\b",
        r"\bmaster deed\b",
        r"\bcc&rs\b",
        r"\bcovenants.*conditions.*restrictions\b",
        r"\bdeclaration of.*association\b",
        r"\bsubmission to condominium ownership\b",
    ]),
    (DocumentType.ARTICLES_OF_INCORPORATION, 9, [
        r"\barticles of incorporation\b",
        r"\bcertificate of incorporation\b",
        r"\bstate of.*department of financial institutions\b",
    ]),
    (DocumentType.RULES_AND_REGULATIONS, 8, [
        r"\brules and regulations\b",
        r"\bhouse rules\b",
        r"\bpet policy\b",
        r"\bparking rules\b",
    ]),
    (DocumentType.ELECTION_RULES, 9, [
        r"\belection rules?\b",
        r"\belection procedure\b",
        r"\belection policy\b",
    ]),
    (DocumentType.BOARD_RESOLUTION, 7, [
        r"\bboard resolution\b",
        r"\bresolution of the board\b",
        r"\bwhereas.*board of directors\b",
    ]),
    (DocumentType.AMENDMENT, 7, [
        r"\bamendment to\b",
        r"\bamendment of\b",
        r"\bfirst amendment\b",
        r"\bsecond amendment\b",
        r"\bamended.*bylaws\b",
        r"\bamended.*declaration\b",
    ]),

    # Meeting history
    (DocumentType.PRIOR_ANNUAL_MINUTES, 10, [
        r"\bannual meeting minutes\b",
        r"\bminutes of.*annual meeting\b",
        r"\bthe annual meeting.*was called to order\b",
        r"\bquorum was (present|established|confirmed)\b",
    ]),
    (DocumentType.PRIOR_ORG_MEETING_MINUTES, 9, [
        r"\borgani[sz]ational meeting minutes\b",
        r"\borganizational meeting of the board\b",
        r"\bfollowing the annual meeting\b",
    ]),
    (DocumentType.PRIOR_ANNUAL_PACKET, 8, [
        r"\bannual meeting packet\b",
        r"\bannual meeting materials\b",
    ]),
    (DocumentType.PRIOR_ANNUAL_NOTICE, 9, [
        r"\bnotice of annual meeting\b",
        r"\byou are hereby notified.*annual meeting\b",
    ]),
    (DocumentType.PRIOR_AGENDA, 8, [
        r"\bmeeting agenda\b",
        r"\bannual meeting agenda\b",
        r"\bagenda.*annual meeting\b",
    ]),
    (DocumentType.PRIOR_PROXY, 9, [
        r"\bproxy.*form\b",
        r"\bproxy.*annual meeting\b",
        r"\bthe undersigned.*hereby appoint\b",
        r"\bproxy holder\b",
    ]),
    (DocumentType.PRIOR_BALLOT, 8, [
        r"\bofficial ballot\b",
        r"\bboard.*election ballot\b",
        r"\bvote for.*director\b",
    ]),

    # Financial
    (DocumentType.CURRENT_BUDGET, 10, [
        r"\b(proposed|approved|adopted)\s+(20\d\d\s+)?budget\b",
        r"\boperating budget\b",
        r"\bannual budget\b",
        r"\bbudget summary\b",
    ]),
    (DocumentType.PRIOR_BUDGET, 6, [
        r"\bprior year budget\b",
        r"\b20\d\d budget\b",
    ]),
    (DocumentType.YTD_FINANCIALS, 9, [
        r"\bstatement of.*income.*expense\b",
        r"\bprofit.*loss.*statement\b",
        r"\bbalance sheet\b",
        r"\byear.to.date\b",
        r"\bfinancial statement\b",
        r"\bincome statement\b",
    ]),
    (DocumentType.PRIOR_YEAR_END_FINANCIALS, 9, [
        r"\byear.end.*financial\b",
        r"\bannual financial.*report\b",
        r"\bfinancial.*year ending\b",
        r"\bstatement of.*year ending\b",
    ]),
    (DocumentType.RESERVE_STUDY, 9, [
        r"\breserve study\b",
        r"\breserve analysis\b",
        r"\breserve fund\b",
        r"\bcapital reserve\b",
    ]),
    (DocumentType.AUDIT_REPORT, 9, [
        r"\bindependent auditor\b",
        r"\baudit report\b",
        r"\bcompilation report\b",
        r"\breview report\b",
        r"\baccountant.*report\b",
    ]),
    (DocumentType.DELINQUENCY_SUMMARY, 8, [
        r"\bdelinquency report\b",
        r"\bpast.due.*assessment\b",
        r"\bcollections report\b",
    ]),

    # Operational
    (DocumentType.BOARD_ROSTER, 9, [
        r"\bboard of directors\b",
        r"\bboard roster\b",
        r"\bcurrent board\b",
        r"\bboard member.*list\b",
    ]),
    (DocumentType.OFFICER_ROSTER, 8, [
        r"\bofficer roster\b",
        r"\bpresident.*vice president.*secretary.*treasurer\b",
        r"\blist of officers\b",
    ]),
    (DocumentType.OWNER_MAILING_LIST, 8, [
        r"\bowner.*list\b",
        r"\bunit.*owner.*address\b",
        r"\bmailing list\b",
        r"\bunit roster\b",
    ]),
    (DocumentType.CANDIDATE_LIST, 8, [
        r"\bcandidate.*list\b",
        r"\bboard.*candidate\b",
        r"\bnomination.*list\b",
    ]),
    (DocumentType.NOMINATION_FORM, 9, [
        r"\bnomination form\b",
        r"\bnominate.*for.*board\b",
        r"\bcandidate.*nomination\b",
        r"\binterest in serving\b",
    ]),
    (DocumentType.MEETING_LOGISTICS, 7, [
        r"\bvenue\b",
        r"\broom reservation\b",
        r"\bmeeting location\b",
        r"\bfacility.*rental\b",
    ]),
]


def classify_document(
    filename: str,
    full_text: str,
    hint: Optional[str] = None,
) -> Tuple[DocumentType, ConfidenceLevel]:
    """
    Return the best-guess DocumentType and a ConfidenceLevel.

    Parameters
    ----------
    filename : str
        Original filename (used for lightweight filename signals).
    full_text : str
        Full extracted text of the document.
    hint : str, optional
        User-supplied label override (plain string matching DocumentType values).
    """
    if hint:
        for dt in DocumentType:
            if hint.lower().replace(" ", "_") == dt.value:
                return dt, ConfidenceLevel.HIGH

    scores: dict[DocumentType, int] = {}
    text_lower = (filename.lower() + " " + full_text.lower())[:50_000]

    for doc_type, weight, patterns in _SIGNALS:
        for pat in patterns:
            if re.search(pat, text_lower, re.IGNORECASE):
                scores[doc_type] = scores.get(doc_type, 0) + weight

    if not scores:
        return DocumentType.UNKNOWN, ConfidenceLevel.LOW

    best_type = max(scores, key=scores.__getitem__)
    best_score = scores[best_type]

    # Confidence thresholds
    if best_score >= 20:
        confidence = ConfidenceLevel.HIGH
    elif best_score >= 10:
        confidence = ConfidenceLevel.MEDIUM
    else:
        confidence = ConfidenceLevel.LOW

    return best_type, confidence
