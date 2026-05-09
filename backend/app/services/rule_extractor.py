"""
Rule extraction engine.

Scans governing-document text for known governance rules using
pattern-matching with source citation tracking.  Results are expressed
as ExtractedRule objects with a confidence level.

DESIGN NOTE:
  This engine uses deterministic regex extraction, not LLM inference.
  All patterns are explicitly authored so a legal reviewer can audit
  exactly what was matched and why.  Add patterns under each rule group
  as governing-document drafting conventions evolve.
"""
from __future__ import annotations
import re
from typing import List, Optional, Tuple
from ..models.document import ExtractedRule, ParsedDocument, ConfidenceLevel


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_number(pattern: str, text: str) -> Optional[int]:
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        raw = m.group(1).strip()
        # convert word numbers
        word_map = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "fifteen": 15, "twenty": 20, "thirty": 30, "sixty": 60,
        }
        if raw.lower() in word_map:
            return word_map[raw.lower()]
        try:
            return int(raw)
        except ValueError:
            return None
    return None


def _find_percent(pattern: str, text: str) -> Optional[float]:
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except (ValueError, IndexError):
            return None
    return None


def _find_text_match(pattern: str, text: str) -> Optional[str]:
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(0).strip()
    return None


def _snippet(text: str, match_pos: int, radius: int = 150) -> str:
    start = max(0, match_pos - radius)
    end = min(len(text), match_pos + radius)
    return text[start:end].strip()


def _make_rule(
    canonical_field: str,
    display_name: str,
    value,
    raw_text: str,
    document_id: str,
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    is_ambiguous: bool = False,
    ambiguity_note: Optional[str] = None,
) -> ExtractedRule:
    return ExtractedRule(
        canonical_field=canonical_field,
        display_name=display_name,
        value=value,
        raw_text=raw_text[:500],
        source_document_id=document_id,
        confidence=confidence,
        is_ambiguous=is_ambiguous,
        ambiguity_note=ambiguity_note,
    )


# ---------------------------------------------------------------------------
# Rule extraction functions — each returns list[ExtractedRule]
# ---------------------------------------------------------------------------

def _word_to_int(raw: str) -> Optional[int]:
    """Convert a word or digit string to int."""
    word_map = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "fifteen": 15, "twenty": 20, "twenty-one": 21, "thirty": 30,
        "forty-five": 45, "sixty": 60, "ninety": 90,
    }
    s = raw.strip().lower()
    if s in word_map:
        return word_map[s]
    try:
        return int(s)
    except ValueError:
        return None


def extract_notice_period(text: str, doc_id: str) -> List[ExtractedRule]:
    rules = []
    # e.g. "not less than 15 days" / "at least 10 days" / "(15) days" / "fifteen (15) days"
    patterns = [
        # "not less than fifteen (15) days" — optional parenthetical digit
        (r"(?:not less than|at least|minimum of|no less than)\s+(\w+(?:-\w+)?)\s*(?:\(\d+\)\s*)?days?", ConfidenceLevel.HIGH),
        # "notice … (15) days before"
        (r"notice[^.]{0,80}?(\d+)\s+days?\s+(?:prior|before|in advance)", ConfidenceLevel.HIGH),
        # plain "15-day notice"
        (r"(\d+|fifteen|twenty|thirty)[- ]?day(?:s)?\s+(?:written\s+)?notice", ConfidenceLevel.MEDIUM),
    ]
    for pat, conf in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            val = _word_to_int(m.group(1))
            if val and 3 <= val <= 90:
                rules.append(_make_rule(
                    "notice_period_days", "Notice Period (days)",
                    val, _snippet(text, m.start()), doc_id, conf,
                ))
                break
        if rules:
            break
    return rules


def extract_notice_max_period(text: str, doc_id: str) -> List[ExtractedRule]:
    rules = []
    patterns = [
        r"(?:not more than|no more than|not to exceed)\s+(\w+(?:-\w+)?)\s+days?\s+(?:before|prior)",
        r"nor\s+more\s+than\s+(\w+(?:-\w+)?)\s+days",
        r"notice.*?but.*?not.*?more.*?than\s+(\w+)\s+days",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            val = _word_to_int(m.group(1))
            if val and 10 <= val <= 120:
                rules.append(_make_rule(
                    "notice_period_max_days", "Notice Period Maximum (days)",
                    val, _snippet(text, m.start()), doc_id, ConfidenceLevel.MEDIUM,
                ))
                break
        if rules:
            break
    return rules


def extract_quorum(text: str, doc_id: str) -> List[ExtractedRule]:
    rules = []
    # Percentage quorum — handles "(25%)", "25 percent", "twenty-five percent (25%)"
    pct_patterns = [
        # "quorum … 25% of" or "quorum … 25 percent of"
        r"quorum[^.]{0,80}?(\d+(?:\.\d+)?)\s*(?:percent|%)",
        # "25% of … constitute a quorum"
        r"(\d+(?:\.\d+)?)\s*(?:percent|%)[^.]{0,80}(?:shall constitute|constitutes|required for)\s*a\s*quorum",
        # "a quorum shall be 25%"
        r"a\s*quorum\s*(?:shall be|is|means)\s*(\d+(?:\.\d+)?)\s*(?:percent|%)",
        # word-number like "twenty-five percent"  followed by parenthetical digit
        r"(?:twenty-five|thirty-three|fifty|sixty-six|seventy-five)\s+percent\s+\((\d+(?:\.\d+)?)\s*%\)",
    ]
    for pat in pct_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                pct = float(m.group(1))
                rules.append(_make_rule(
                    "quorum_threshold_pct", "Quorum Threshold (%)",
                    pct, _snippet(text, m.start()), doc_id, ConfidenceLevel.HIGH,
                ))
                return rules
            except (ValueError, IndexError):
                pass

    # Fractional quorum
    fraction_patterns = [
        r"quorum.*?(one.third|one.half|two.thirds?|three.quarters?|majority)\s*(?:of|in)",
        r"(one.third|one.half|two.thirds?|three.quarters?|majority)\s*(?:of\b[^.]{0,40})?(?:votes?|units?|members?|owners?)?[^.]{0,30}(?:shall constitute|constitutes)\s*a\s*quorum",
        r"(majority|one.third|one.half|two.thirds?)\s+of\s+the\s+(?:members?|owners?|votes?)[^.]*(?:shall constitute|constitutes|present shall constitute)\s*a\s*quorum",
    ]
    fraction_map = {
        "one-third": 33.33, "one third": 33.33,
        "one-half": 50.0, "one half": 50.0,
        "majority": 50.01,
        "two-thirds": 66.67, "two thirds": 66.67,
        "three-quarters": 75.0, "three quarters": 75.0,
    }
    for pat in fraction_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw = m.group(1).lower().replace("\n", " ").strip()
            normalized = re.sub(r"\s+", " ", raw)
            for key, val in fraction_map.items():
                if key in normalized:
                    rules.append(_make_rule(
                        "quorum_threshold_pct", "Quorum Threshold (%)",
                        val, _snippet(text, m.start()), doc_id, ConfidenceLevel.MEDIUM,
                        is_ambiguous=True,
                        ambiguity_note=f"Quorum expressed as fraction '{raw}'; converted to {val}%",
                    ))
                    return rules

    return rules


def extract_proxy_rules(text: str, doc_id: str) -> List[ExtractedRule]:
    rules = []
    if re.search(r"\bprox(?:y|ies)\b", text, re.IGNORECASE):
        # Proxy permitted
        rules.append(_make_rule(
            "proxy_permitted", "Proxy Voting Permitted",
            True, _snippet(text, text.lower().find("prox")), doc_id, ConfidenceLevel.HIGH,
        ))
        # Single-meeting proxy (use DOTALL for multi-line text)
        if re.search(r"proxy[^.]*?(?:valid|effective)[^.]*?(?:only for|for only|solely for)\s+(?:the|this|that)\s+(?:specific|particular|designated)?\s*meeting", text, re.IGNORECASE | re.DOTALL):
            rules.append(_make_rule(
                "proxy_single_meeting", "Proxy Valid for Single Meeting Only",
                True, "", doc_id, ConfidenceLevel.HIGH,
            ))
        # Proxy deadline
        m = re.search(r"proxy.*?(?:must|shall)\s+(?:be\s+)?(?:received|submitted|delivered).*?(\d+)\s+(?:hours?|days?)\s+(?:before|prior)", text, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            unit = "hours" if "hour" in m.group(0).lower() else "days"
            rules.append(_make_rule(
                "proxy_deadline", "Proxy Submission Deadline",
                f"{val} {unit} before meeting", _snippet(text, m.start()), doc_id, ConfidenceLevel.MEDIUM,
            ))
    else:
        rules.append(_make_rule(
            "proxy_permitted", "Proxy Voting Permitted",
            False, "No proxy language found", doc_id, ConfidenceLevel.LOW,
            is_ambiguous=True,
            ambiguity_note="No proxy language found in document; confirm with bylaws",
        ))
    return rules


def extract_election_rules(text: str, doc_id: str) -> List[ExtractedRule]:
    rules = []

    # Annual elections
    election_patterns = [
        r"(?:director|board member)s?\s*(?:shall be|are)\s*elected\s*(?:at|during|by)\s*(?:the\s+)?(?:unit\s+owners?|members?|owners?)\s+(?:at|during|each)\s*(?:the\s+)?annual meeting",
        r"(?:director|board member)s?\s*(?:shall be|are)\s*elected\s*(?:at|during)\s*(?:the|each)\s*annual meeting",
        r"elect(?:ed)?\s+(?:directors?|board members?)\s+at\s+(?:the|each)\s+annual meeting",
        r"directors?\s+shall be elected\s+by\s+the\s+unit owners?\s+at\s+each\s+annual meeting",
    ]
    for epat in election_patterns:
        if re.search(epat, text, re.IGNORECASE):
            rules.append(_make_rule(
                "election_at_annual_meeting", "Elections Held at Annual Meeting",
                True, "", doc_id, ConfidenceLevel.HIGH,
            ))
            break

    # Term length — capture group 1 has the number/word
    term_patterns = [
        # "shall serve three-year (3-year) terms" — optional parenthetical
        r"(?:director|board member)s?\s*(?:shall serve|serve)[^.]{0,30}(\w+)[- ]year(?:s?)\s*(?:\(\d+[- ]year(?:s?)?\)\s*)?terms?",
        # plain "three-year (3-year) staggered terms"
        r"(\w+)[- ]year(?:s?)\s*(?:\(\d+[- ]year(?:s?)?\)\s*)?\w*\s*terms?\b",
        # "terms of three years"
        r"term(?:s)?\s+of\s+(\w+)\s+years?",
    ]
    for tpat in term_patterns:
        term_m = re.search(tpat, text, re.IGNORECASE)
        if term_m:
            val = _word_to_int(term_m.group(1))
            if val and 1 <= val <= 10:
                rules.append(_make_rule(
                    "director_term_years", "Director Term Length (years)",
                    val, _snippet(text, term_m.start()), doc_id, ConfidenceLevel.HIGH,
                ))
                break

    # Staggered terms — match "staggered" anywhere near "terms" context
    stagger_patterns = [
        r"stagger(?:ed)?\s+term",
        r"terms[^.]{0,60}\bstagger(?:ed)?\b",
        r"\bstagger(?:ed)?\b[^.]{0,80}(?:term|expire|seat)",
    ]
    for spat in stagger_patterns:
        if re.search(spat, text, re.IGNORECASE):
            rules.append(_make_rule(
                "staggered_terms", "Staggered Director Terms",
                True, "", doc_id, ConfidenceLevel.HIGH,
            ))
            break

    # Board size — allow parenthetical "(5)" between word and "directors"
    bsize_patterns = [
        r"board\s+(?:of\s+directors\s+)?(?:shall consist of|consists of|shall have)\s+(\w+)\s*(?:\(\d+\)\s*)?(?:director|member)",
        r"(\w+)\s*(?:\(\d+\)\s+)?directors?\s+(?:shall|who\s+shall)\s+(?:serve|be elected|manage)",
        r"consist(?:s|ing)?\s+of\s+(\w+)\s*(?:\(\d+\)\s*)?directors?",
    ]
    for bpat in bsize_patterns:
        m = re.search(bpat, text, re.IGNORECASE)
        if m:
            val = _word_to_int(m.group(1))
            if val and 1 <= val <= 25:
                rules.append(_make_rule(
                    "board_size", "Board Size",
                    val, _snippet(text, m.start()), doc_id, ConfidenceLevel.HIGH,
                ))
                break

    # Floor nominations
    if re.search(r"nominat(?:ion|e)s?\s+(?:may|shall|can)\s+(?:also\s+)?be\s+(?:made\s+)?from\s+the\s+floor", text, re.IGNORECASE):
        rules.append(_make_rule(
            "nominations_from_floor", "Floor Nominations Permitted",
            True, "", doc_id, ConfidenceLevel.HIGH,
        ))

    return rules


def extract_financial_reporting_rules(text: str, doc_id: str) -> List[ExtractedRule]:
    rules = []

    if re.search(r"annual\s+(?:financial\s+)?report(?:ing)?\s+(?:shall be|must be|is|to be)\s+(?:provided|distributed|prepared|sent)\s+(?:to\s+unit\s+owners?|to\s+members?)", text, re.IGNORECASE):
        rules.append(_make_rule(
            "annual_financial_report_required", "Annual Financial Report Required",
            True, "", doc_id, ConfidenceLevel.HIGH,
        ))

    if re.search(r"(?:annual\s+)?(?:accounting|financial\s+report).*?(?:within|by|not later than|no later than)\s+(\w+)\s+days?\s+(?:after|following|of)\s+(?:the\s+)?(?:end\s+of\s+the\s+)?fiscal\s+year", text, re.IGNORECASE):
        rules.append(_make_rule(
            "financial_report_timing", "Financial Report Timing",
            "Required by end of fiscal year or within period specified",
            "", doc_id, ConfidenceLevel.MEDIUM,
        ))

    return rules


def extract_meeting_requirement(text: str, doc_id: str) -> List[ExtractedRule]:
    rules = []
    if re.search(r"annual\s+meeting\s+(?:of\s+(?:the\s+)?(?:unit\s+owners?|members?))\s+(?:shall be held|shall be|must be held|is required)", text, re.IGNORECASE):
        rules.append(_make_rule(
            "annual_meeting_required", "Annual Meeting Required",
            True, "", doc_id, ConfidenceLevel.HIGH,
        ))

    # Timing window
    m = re.search(
        r"annual\s+meeting.*?(?:held|occur).*?(?:between|during)\s+(?:the\s+months?\s+of\s+)?(\w+)\s+and\s+(\w+)",
        text, re.IGNORECASE
    )
    if m:
        rules.append(_make_rule(
            "annual_meeting_window", "Annual Meeting Timing Window",
            f"{m.group(1)} - {m.group(2)}", _snippet(text, m.start()), doc_id, ConfidenceLevel.MEDIUM,
        ))

    return rules


def extract_org_meeting_requirement(text: str, doc_id: str) -> List[ExtractedRule]:
    rules = []
    if re.search(
        r"(?:"
        r"organi[sz]ational\s+meeting[^.]{0,80}(?:following|after)\s+(?:the\s+)?annual\s+meeting"
        r"|(?:immediately\s+)?following[^.]{0,80}annual\s+meeting[^.]{0,80}organi[sz]ational\s+meeting"
        r")",
        text, re.IGNORECASE | re.DOTALL
    ):
        rules.append(_make_rule(
            "org_meeting_after_annual", "Organizational Meeting Required After Annual Meeting",
            True, "", doc_id, ConfidenceLevel.HIGH,
        ))
    return rules


def extract_vote_per_unit(text: str, doc_id: str) -> List[ExtractedRule]:
    rules = []
    if re.search(r"one\s+(?:\(1\)\s+)?vote\s+(?:per|for each)\s+unit", text, re.IGNORECASE):
        rules.append(_make_rule(
            "vote_structure", "Voting Structure",
            "one_vote_per_unit", "", doc_id, ConfidenceLevel.HIGH,
        ))
    elif re.search(r"percentage\s+interest.*?vote", text, re.IGNORECASE):
        rules.append(_make_rule(
            "vote_structure", "Voting Structure",
            "weighted_by_percentage", "", doc_id, ConfidenceLevel.MEDIUM,
            is_ambiguous=True,
            ambiguity_note="Weighted by percentage interest suggested; confirm in declaration",
        ))
    return rules


def extract_adjournment_rules(text: str, doc_id: str) -> List[ExtractedRule]:
    rules = []
    m = re.search(
        r"(?:if|should|when)\s+(?:a\s+)?quorum\s+(?:is\s+not|cannot be|fails to be)\s+(?:present|achieved|obtained).*?(?:adjourned?|reconvened?)",
        text, re.IGNORECASE | re.DOTALL
    )
    if m:
        rules.append(_make_rule(
            "adjournment_if_no_quorum", "Adjournment Rules if No Quorum",
            _snippet(text, m.start(), 200),
            _snippet(text, m.start()), doc_id, ConfidenceLevel.MEDIUM,
        ))
    return rules


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

_EXTRACTORS = [
    extract_meeting_requirement,
    extract_notice_period,
    extract_notice_max_period,
    extract_quorum,
    extract_proxy_rules,
    extract_election_rules,
    extract_financial_reporting_rules,
    extract_org_meeting_requirement,
    extract_vote_per_unit,
    extract_adjournment_rules,
]


def extract_rules(parsed_doc: ParsedDocument) -> List[ExtractedRule]:
    """
    Run all extractors against a parsed document.
    Returns deduplicated list of ExtractedRule, highest-confidence first.
    """
    rules: List[ExtractedRule] = []
    text = parsed_doc.full_text

    if not text.strip():
        return rules

    for extractor in _EXTRACTORS:
        try:
            new_rules = extractor(text, parsed_doc.document_id)
            rules.extend(new_rules)
        except Exception:
            pass

    # Deduplicate: keep highest confidence per canonical_field
    best: dict[str, ExtractedRule] = {}
    conf_rank = {
        ConfidenceLevel.HIGH: 3,
        ConfidenceLevel.MEDIUM: 2,
        ConfidenceLevel.LOW: 1,
        ConfidenceLevel.UNVERIFIED: 0,
    }
    for rule in rules:
        existing = best.get(rule.canonical_field)
        if existing is None or conf_rank.get(rule.confidence, 0) > conf_rank.get(existing.confidence, 0):
            best[rule.canonical_field] = rule

    return list(best.values())
