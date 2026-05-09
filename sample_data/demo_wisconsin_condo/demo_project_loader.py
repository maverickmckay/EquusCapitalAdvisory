"""
Demo project loader.

Creates the Wisconsin demo project with pre-populated data so
you can immediately see a generated packet without uploading files.

Run:
    cd backend
    python -m sample_data.demo_wisconsin_condo.demo_project_loader
"""
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import date
from backend.app.models.association import AssociationProfile, AssociationType, VoteStructure
from backend.app.models.meeting import MeetingProfile, QuorumBasis, AgendaItem
from backend.app.models.packet import (
    ProjectState, FinancialProfile, ElectionProfile,
    BoardMember, BoardSeat, CandidateBio, PacketSections
)
from backend.app.services.project_store import save_project
from backend.app.services.jurisdiction_loader import load_jurisdiction
from backend.app.services.missing_analyzer import analyze_missing_items
from backend.app.services.validator import run_validation
from backend.app.services.packet_generator import generate_packet


def create_demo_project() -> ProjectState:
    assoc = AssociationProfile(
        association_name="Lakeside Condominium Association, Inc.",
        state="WI",
        association_type=AssociationType.CONDOMINIUM,
        meeting_year=2026,
        unit_count=48,
        vote_structure=VoteStructure.ONE_VOTE_PER_UNIT,
        management_company="Premiere Property Management, LLC",
        management_contact="Lisa Hoffman, CAM",
        management_email="lhoffman@premierepm.com",
        management_phone="608-555-9100",
    )

    meeting = MeetingProfile(
        meeting_date=date(2026, 3, 17),
        meeting_time="6:00 PM CST",
        registration_time="5:45 PM",
        meeting_location="Community Room, Lakeside Condominiums",
        meeting_address="500 Lakeside Drive, Madison, WI 53703",
        notice_date=date(2026, 2, 27),
        notice_period_min_days=15,
        notice_period_max_days=60,
        quorum_threshold=25.0,
        quorum_basis=QuorumBasis.PERCENTAGE_OF_VOTES,
        quorum_threshold_raw="25% of total votes",
        adjournment_rules="If quorum is not present, the meeting shall be adjourned to a date and time set by the Chair.",
        proxy_permitted=True,
        proxy_deadline=date(2026, 3, 16),
        proxy_revocable=True,
        proxy_valid_for_single_meeting=True,
        agenda_items=[
            AgendaItem(order=1, title="Call to Order"),
            AgendaItem(order=2, title="Proof of Notice"),
            AgendaItem(order=3, title="Establishment of Quorum"),
            AgendaItem(order=4, title="Approval of Agenda"),
            AgendaItem(order=5, title="Approval of 2025 Annual Meeting Minutes"),
            AgendaItem(order=6, title="Election of Three (3) Directors to the Board", requires_vote=True),
            AgendaItem(order=7, title="Treasurer's Report / Financial Report", description="Presentation of 2025 year-end financials and 2026 approved budget."),
            AgendaItem(order=8, title="Old Business"),
            AgendaItem(order=9, title="New Business"),
            AgendaItem(order=10, title="Adjournment"),
        ]
    )

    financial = FinancialProfile(
        approved_budget_year=2026,
        approved_budget_total=169700.00,
        approved_budget_notes="$5/unit/month assessment increase effective January 1, 2026.",
        prior_budget_total=162000.00,
        prior_year_end_income=165_800.00,
        prior_year_end_expenses=162_340.00,
        prior_year_end_net=3_460.00,
        reserve_fund_balance=127_450.00,
        reserve_percent_funded=62.0,
        reserve_study_year=2023,
        audit_completed=False,
        key_budget_line_items={
            "Management Fees": 18000.00,
            "Insurance (Liability + Property)": 20600.00,
            "Landscaping & Snow Removal": 22000.00,
            "Building & Common Area Maintenance": 29200.00,
            "Utilities (Water, Gas, Electric, Trash)": 33000.00,
            "Legal, Accounting & Admin": 7300.00,
            "Reserve Fund Contribution": 38800.00,
        },
        key_financial_notes=[
            "2025 resulted in a net surplus of $3,460, primarily due to lower-than-expected snow removal costs.",
            "Reserve fund is 62% funded per the 2023 reserve study. Board intends to update study in 2026.",
            "No special assessments were levied in 2025.",
        ],
        financial_source_docs=["2026 Approved Budget (Board adopted Nov. 19, 2025)", "2025 Unaudited Year-End Financials"],
    )

    election = ElectionProfile(
        election_required=True,
        election_reason="Three board seats expire at the 2026 Annual Meeting per staggered-term schedule.",
        board_size=5,
        director_term_length_years=3,
        staggered_terms=True,
        seats_up_count=3,
        nomination_from_floor=True,
        board_roster=[
            BoardMember(name="Margaret Chen", unit_number="204", title="Director", officer_title="President",
                        term_start=date(2025,1,1), term_end=date(2027,12,31), term_length_years=3, is_officer=True, seat_up_this_year=False),
            BoardMember(name="Robert Kowalski", unit_number="117", title="Director", officer_title="Vice President",
                        term_start=date(2024,1,1), term_end=date(2026,12,31), term_length_years=3, is_officer=True, seat_up_this_year=True),
            BoardMember(name="Sandra Williams", unit_number="312", title="Director", officer_title="Secretary",
                        term_start=date(2025,1,1), term_end=date(2027,12,31), term_length_years=3, is_officer=True, seat_up_this_year=False),
            BoardMember(name="David Park", unit_number="108", title="Director", officer_title="Treasurer",
                        term_start=date(2024,1,1), term_end=date(2026,12,31), term_length_years=3, is_officer=True, seat_up_this_year=True),
            BoardMember(name="James O'Brien", unit_number="415", title="Director",
                        term_start=date(2022,1,1), term_end=date(2025,12,31), term_length_years=3, is_officer=False, seat_up_this_year=True,
                        notes="Holdover director — term expired December 2025"),
        ],
        seat_map=[
            BoardSeat(seat_label="Seat A", current_occupant="Robert Kowalski", term_length_years=3, term_expiry_year=2026, up_for_election=True, incumbent_running=True),
            BoardSeat(seat_label="Seat B", current_occupant="David Park", term_length_years=3, term_expiry_year=2026, up_for_election=True, incumbent_running=True),
            BoardSeat(seat_label="Seat C", current_occupant="James O'Brien", term_length_years=3, term_expiry_year=2025, up_for_election=True, incumbent_running=False),
        ],
        candidate_bios=[
            CandidateBio(
                name="Robert Kowalski",
                unit_number="117",
                bio_text="Rob has served on the Board since 2021 and currently serves as Vice President. "
                         "He is a licensed civil engineer with 20 years of experience in infrastructure projects. "
                         "Rob led the 2024 parking lot resurfacing project and the lobby renovation committee.",
                years_in_community=8,
                relevant_experience="Licensed Civil Engineer (PE), experienced in construction oversight and capital planning.",
                why_running="I am seeking re-election to continue overseeing the association's capital improvement program and reserve planning.",
                incumbent=True,
            ),
            CandidateBio(
                name="David Park",
                unit_number="108",
                bio_text="David has served as Treasurer since 2021. He is a CPA with expertise in nonprofit accounting. "
                         "Under his stewardship, the association's reserve fund has grown from $98,000 to $127,000.",
                years_in_community=6,
                relevant_experience="Certified Public Accountant (CPA); partner at a local accounting firm.",
                why_running="I want to continue my work on reserve funding and financial transparency for all owners.",
                incumbent=True,
            ),
            CandidateBio(
                name="Patricia Nguyen",
                unit_number="220",
                bio_text="Patricia is a new candidate for the Board. She is a retired school principal with extensive "
                         "experience in community leadership and organizational management. She has lived at Lakeside "
                         "for 4 years and is passionate about community communication and maintenance standards.",
                years_in_community=4,
                relevant_experience="30-year career in education administration; community volunteer and HOA committee member.",
                why_running="I would like to bring fresh perspectives and strong communication skills to the Board.",
                incumbent=False,
            ),
        ],
    )

    sections = PacketSections(
        cover_page=True,
        table_of_contents=True,
        notice=True,
        agenda=True,
        proxy=True,
        nomination_form=True,
        candidate_bios=True,
        financial_summary=True,
        budget_summary=True,
        prior_minutes_status=True,
        election_explanation=True,
        bylaw_excerpts=False,
        meeting_instructions=True,
        minutes_template=True,
        validation_appendix=False,
    )

    state = ProjectState(
        project_name="Lakeside Condominiums — 2026 Annual Meeting (DEMO)",
        association=assoc,
        meeting=meeting,
        financial=financial,
        election=election,
        packet_sections=sections,
    )

    # Load jurisdiction rules
    state.jurisdiction_rules = load_jurisdiction("WI")

    # Populate extracted rules to simulate bylaw parsing
    state.extracted_rules = {
        "annual_meeting_required": {"canonical_field": "annual_meeting_required", "display_name": "Annual Meeting Required", "value": True, "confidence": "high", "is_ambiguous": False, "raw_text": "...annual meeting of unit owners...shall be held each year...", "source_document_id": "demo-bylaws"},
        "notice_period_days": {"canonical_field": "notice_period_days", "display_name": "Notice Period (days)", "value": 15, "confidence": "high", "is_ambiguous": False, "raw_text": "...not less than fifteen (15) days...", "source_document_id": "demo-bylaws"},
        "notice_period_max_days": {"canonical_field": "notice_period_max_days", "display_name": "Notice Period Maximum (days)", "value": 60, "confidence": "high", "is_ambiguous": False, "raw_text": "...nor more than sixty (60) days...", "source_document_id": "demo-bylaws"},
        "quorum_threshold_pct": {"canonical_field": "quorum_threshold_pct", "display_name": "Quorum Threshold (%)", "value": 25.0, "confidence": "high", "is_ambiguous": False, "raw_text": "...twenty-five percent (25%) of the total votes...", "source_document_id": "demo-bylaws"},
        "proxy_permitted": {"canonical_field": "proxy_permitted", "display_name": "Proxy Voting Permitted", "value": True, "confidence": "high", "is_ambiguous": False, "raw_text": "...A unit owner may vote by proxy...", "source_document_id": "demo-bylaws"},
        "proxy_single_meeting": {"canonical_field": "proxy_single_meeting", "display_name": "Proxy Valid for Single Meeting Only", "value": True, "confidence": "high", "is_ambiguous": False, "raw_text": "...effective only for the specific meeting...", "source_document_id": "demo-bylaws"},
        "election_at_annual_meeting": {"canonical_field": "election_at_annual_meeting", "display_name": "Elections Held at Annual Meeting", "value": True, "confidence": "high", "is_ambiguous": False, "raw_text": "...Directors shall be elected by the unit owners at each annual meeting...", "source_document_id": "demo-bylaws"},
        "director_term_years": {"canonical_field": "director_term_years", "display_name": "Director Term Length (years)", "value": 3, "confidence": "high", "is_ambiguous": False, "raw_text": "...three-year (3-year) terms...", "source_document_id": "demo-bylaws"},
        "staggered_terms": {"canonical_field": "staggered_terms", "display_name": "Staggered Director Terms", "value": True, "confidence": "high", "is_ambiguous": False, "raw_text": "...terms of directors shall be staggered...", "source_document_id": "demo-bylaws"},
        "board_size": {"canonical_field": "board_size", "display_name": "Board Size", "value": 5, "confidence": "high", "is_ambiguous": False, "raw_text": "...Board of Directors shall consist of five (5) directors...", "source_document_id": "demo-bylaws"},
        "org_meeting_after_annual": {"canonical_field": "org_meeting_after_annual", "display_name": "Organizational Meeting Required After Annual Meeting", "value": True, "confidence": "high", "is_ambiguous": False, "raw_text": "...Immediately following the annual meeting of unit owners, the Board...shall hold an organizational meeting...", "source_document_id": "demo-bylaws"},
        "annual_financial_report_required": {"canonical_field": "annual_financial_report_required", "display_name": "Annual Financial Report Required", "value": True, "confidence": "high", "is_ambiguous": False, "raw_text": "...provide each unit owner with a written itemized annual accounting...", "source_document_id": "demo-bylaws"},
        "vote_structure": {"canonical_field": "vote_structure", "display_name": "Voting Structure", "value": "one_vote_per_unit", "confidence": "high", "is_ambiguous": False, "raw_text": "...one (1) vote per unit owned...", "source_document_id": "demo-bylaws"},
    }

    state.manual_entries = {
        "prior_minutes_status": "available",
        "election_required": True,
    }

    return state


def main():
    print("Creating Wisconsin Demo Project...")
    state = create_demo_project()

    state.document_status = analyze_missing_items(state)

    from backend.app.services.validator import run_validation, validation_summary
    validation_results = run_validation(state)
    vsummary = validation_summary(validation_results)

    print(f"\nValidation Summary:")
    print(f"  Ready to Generate: {vsummary['ready_to_generate']}")
    print(f"  Blockers: {vsummary['blocker_count']}")
    print(f"  Warnings: {vsummary['warning_count']}")
    print(f"  Passes: {vsummary['pass_count']}")

    print("\nGenerating LaTeX packet...")
    from pathlib import Path
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    result = generate_packet(state, output_dir=output_dir, compile_pdf=False)

    if result["success"]:
        print(f"\n✓ SUCCESS!")
        print(f"  .tex file: {result['tex_path']}")
        if result.get("pdf_path"):
            print(f"  PDF file: {result['pdf_path']}")
        if result.get("errors"):
            print(f"  Notes: {result['errors']}")
    else:
        print(f"\n✗ FAILED: {result['errors']}")

    save_project(state)
    print(f"\nProject ID: {state.project_id}")
    print("You can open this project at: http://localhost:8000/projects/" + state.project_id)

    return state


if __name__ == "__main__":
    main()
