"""
Document upload and classification routes.
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from ..models.document import UploadedDocument, DocumentType, ConfidenceLevel
from ..services.document_parser import parse_document
from ..services.classifier import classify_document
from ..services.rule_extractor import extract_rules
from ..services.missing_analyzer import analyze_missing_items
from ..services.project_store import (
    load_project, save_project, save_upload, get_upload_path
)
from ..config import MAX_UPLOAD_MB, ALLOWED_EXTENSIONS

router = APIRouter(prefix="/api/projects/{project_id}/documents", tags=["documents"])

MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024


@router.post("")
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    document_type_hint: Optional[str] = Form(None),
):
    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{suffix}' not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail=f"File exceeds {MAX_UPLOAD_MB} MB limit.")

    # Create document record
    doc = UploadedDocument(
        filename=file.filename,
        original_filename=file.filename,
        file_size_bytes=len(content),
        mime_type=file.content_type,
    )

    # Save file to disk
    save_upload(project_id, doc.document_id + suffix, content)
    file_path = get_upload_path(project_id, doc.document_id + suffix)

    # Parse
    try:
        parsed = parse_document(doc, file_path)
        doc.parsed = True
        if parsed.parse_errors:
            doc.parse_error = "; ".join(parsed.parse_errors)
    except Exception as e:
        doc.parsed = False
        doc.parse_error = str(e)
        parsed = None

    # Classify
    full_text = parsed.full_text if parsed else ""
    doc_type, confidence = classify_document(file.filename, full_text, document_type_hint)
    doc.document_type = doc_type
    doc.classification_confidence = confidence
    if document_type_hint:
        doc.user_confirmed_type = True

    # Extract rules if it's a governing document
    if parsed and doc_type in (
        DocumentType.BYLAWS,
        DocumentType.DECLARATION,
        DocumentType.ARTICLES_OF_INCORPORATION,
        DocumentType.ELECTION_RULES,
    ):
        rules = extract_rules(parsed)
        for rule in rules:
            rule_dict = rule.dict()
            existing = state.extracted_rules.get(rule.canonical_field)
            if existing is None:
                state.extracted_rules[rule.canonical_field] = rule_dict
            else:
                # Keep higher confidence
                from ..models.document import ConfidenceLevel
                conf_rank = {
                    ConfidenceLevel.HIGH: 3, ConfidenceLevel.MEDIUM: 2,
                    ConfidenceLevel.LOW: 1, ConfidenceLevel.UNVERIFIED: 0,
                }
                if conf_rank.get(rule.confidence, 0) > conf_rank.get(existing.get("confidence"), 0):
                    state.extracted_rules[rule.canonical_field] = rule_dict

        # Apply extracted rules to meeting/election profiles
        _apply_extracted_rules(state)

    # Add document to state
    state.document_status.uploaded_docs.append(doc)
    if parsed:
        state.document_status.parsed_doc_ids.append(doc.document_id)

    # Re-run missing analysis
    state.document_status = analyze_missing_items(state)
    save_project(state)

    return {
        "document_id": doc.document_id,
        "filename": doc.filename,
        "document_type": doc.document_type,
        "classification_confidence": doc.classification_confidence,
        "parsed": doc.parsed,
        "parse_error": doc.parse_error,
        "extracted_rules_count": len(state.extracted_rules),
    }


@router.get("")
def list_documents(project_id: str):
    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"documents": [d.dict() for d in state.document_status.uploaded_docs]}


@router.put("/{document_id}/type")
def reclassify_document(project_id: str, document_id: str, document_type: str):
    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    doc = next((d for d in state.document_status.uploaded_docs if d.document_id == document_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        doc.document_type = DocumentType(document_type)
        doc.user_confirmed_type = True
        doc.classification_confidence = ConfidenceLevel.HIGH
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown document type: {document_type}")

    state.document_status = analyze_missing_items(state)
    save_project(state)
    return {"ok": True, "document_id": document_id, "new_type": document_type}


@router.delete("/{document_id}")
def delete_document(project_id: str, document_id: str):
    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    original_count = len(state.document_status.uploaded_docs)
    state.document_status.uploaded_docs = [
        d for d in state.document_status.uploaded_docs if d.document_id != document_id
    ]
    if len(state.document_status.uploaded_docs) == original_count:
        raise HTTPException(status_code=404, detail="Document not found")

    state.document_status = analyze_missing_items(state)
    save_project(state)
    return {"ok": True}


@router.get("/rules")
def get_extracted_rules(project_id: str):
    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"rules": state.extracted_rules}


def _apply_extracted_rules(state) -> None:
    """Apply extracted rules to the meeting/election profile as defaults."""
    rules = state.extracted_rules

    if "notice_period_days" in rules and state.meeting.notice_period_min_days is None:
        state.meeting.notice_period_min_days = rules["notice_period_days"].get("value")

    if "notice_period_max_days" in rules and state.meeting.notice_period_max_days is None:
        state.meeting.notice_period_max_days = rules["notice_period_max_days"].get("value")

    if "quorum_threshold_pct" in rules and state.meeting.quorum_threshold is None:
        state.meeting.quorum_threshold = rules["quorum_threshold_pct"].get("value")

    if "proxy_permitted" in rules and state.meeting.proxy_permitted is None:
        state.meeting.proxy_permitted = rules["proxy_permitted"].get("value")

    if "proxy_single_meeting" in rules:
        state.meeting.proxy_valid_for_single_meeting = rules["proxy_single_meeting"].get("value", True)

    if "election_at_annual_meeting" in rules:
        if not state.election.election_required:
            state.election.election_required = rules["election_at_annual_meeting"].get("value")

    if "director_term_years" in rules and state.election.director_term_length_years is None:
        state.election.director_term_length_years = rules["director_term_years"].get("value")

    if "staggered_terms" in rules:
        state.election.staggered_terms = rules["staggered_terms"].get("value", False)

    if "board_size" in rules and state.election.board_size is None:
        state.election.board_size = rules["board_size"].get("value")
