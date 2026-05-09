"""
Unit tests for the document classifier.
"""
import pytest
from backend.app.models.document import DocumentType, ConfidenceLevel
from backend.app.services.classifier import classify_document


class TestClassifier:
    def test_bylaws_classification(self):
        text = "BYLAWS OF RIVERVIEW ASSOCIATION. Article III — Meetings of members. The annual meeting shall..."
        doc_type, conf = classify_document("bylaws.pdf", text)
        assert doc_type == DocumentType.BYLAWS
        assert conf in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)

    def test_declaration_classification(self):
        text = "DECLARATION OF CONDOMINIUM for Pine Ridge Condominiums, a Wisconsin condominium. Submission to condominium ownership."
        doc_type, conf = classify_document("declaration.pdf", text)
        assert doc_type == DocumentType.DECLARATION

    def test_budget_classification(self):
        text = "APPROVED OPERATING BUDGET — FISCAL YEAR 2026. Total budgeted income: $150,000. Annual budget summary."
        doc_type, conf = classify_document("budget_2026.pdf", text)
        assert doc_type == DocumentType.CURRENT_BUDGET

    def test_board_roster_classification(self):
        text = "Board of Directors — Current Roster. President: Jane Smith. Vice President: John Doe."
        doc_type, conf = classify_document("board_roster.txt", text)
        assert doc_type == DocumentType.BOARD_ROSTER

    def test_proxy_classification(self):
        text = "PROXY FOR ANNUAL MEETING. The undersigned unit owner hereby appoints _____ as proxy holder."
        doc_type, conf = classify_document("proxy_form.pdf", text)
        assert doc_type == DocumentType.PRIOR_PROXY

    def test_annual_minutes_classification(self):
        text = "MINUTES OF THE ANNUAL MEETING OF UNIT OWNERS. Quorum was present. The annual meeting was called to order."
        doc_type, conf = classify_document("minutes_2025.pdf", text)
        assert doc_type == DocumentType.PRIOR_ANNUAL_MINUTES

    def test_financials_classification(self):
        text = "STATEMENT OF INCOME AND EXPENSES. Year ending December 31, 2025. Total income: $160,000."
        doc_type, conf = classify_document("financials.pdf", text)
        assert doc_type in (DocumentType.YTD_FINANCIALS, DocumentType.PRIOR_YEAR_END_FINANCIALS)

    def test_user_hint_overrides_classification(self):
        text = "Some random text that doesn't match any pattern."
        doc_type, conf = classify_document("random.pdf", text, hint="bylaws")
        assert doc_type == DocumentType.BYLAWS
        assert conf == ConfidenceLevel.HIGH

    def test_unknown_file_classified_unknown(self):
        text = "Random content with no governance keywords whatsoever."
        doc_type, conf = classify_document("random_file.pdf", text)
        assert doc_type == DocumentType.UNKNOWN

    def test_reserve_study_classification(self):
        text = "RESERVE STUDY for Maplewood Association. Reserve fund analysis. Capital reserve funding level 65%."
        doc_type, conf = classify_document("reserve_study.pdf", text)
        assert doc_type == DocumentType.RESERVE_STUDY

    def test_nomination_form_classification(self):
        text = "NOMINATION FORM for Board of Directors. I am interested in serving on the board. Candidate nomination."
        doc_type, conf = classify_document("nomination_form.pdf", text)
        assert doc_type == DocumentType.NOMINATION_FORM
