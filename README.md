# HOA Annual Meeting Packet Generator

A production-ready local application that ingests HOA and condominium association governing documents and operational files, extracts meeting rules, identifies missing information, validates compliance, and generates a professional annual meeting packet as a LaTeX/PDF file.

Designed for property managers, HOA attorneys, board administrators, and compliance teams.

---

## What It Does

1. **Auto-classifies uploaded documents** — Bylaws, financials, board rosters, prior minutes, and more are recognized automatically.
2. **Extracts governance rules** — Notice periods, quorum thresholds, proxy rules, election procedures, and director terms are parsed directly from governing documents.
3. **Identifies missing items** — The system tells you exactly what is missing, why it matters, and how to resolve it, with BLOCKER / REQUIRED / CONDITIONAL / RECOMMENDED severity levels.
4. **Validates compliance** — Notice period compliance, quorum logic, election consistency, proxy authorization, and financial reporting obligations are validated before generation.
5. **Generates a professional LaTeX packet** — Annual notice, agenda, proxy, candidate forms, candidate bios, financial summary, minutes status, election explanation, meeting instructions, and draft minutes template.
6. **Supports any association** — Rule-driven, not template-based. Works for any HOA, condo, co-op, or townhome association in any US state.
7. **State-specific law overlays** — Wisconsin fully implemented; Illinois scaffold included; additional states easy to add via YAML.

---

## Quick Start (Local)

### Prerequisites

- Python 3.10 or newer
- pip

Optional for PDF output:
- TeX Live or MiKTeX (`pdflatex` or `latexmk`)

### Installation

```bash
git clone <this-repo>
cd EquusCapitalAdvisory
pip install -r requirements.txt
```

### Run the Application

```bash
uvicorn backend.app.main:app --reload --port 8000
```

Open your browser at **http://localhost:8000**

### Load the Wisconsin Demo Project

To immediately see a generated packet without uploading files:

```bash
python -m sample_data.demo_wisconsin_condo.demo_project_loader
```

This creates a fully populated Wisconsin condo demo project, runs validation, and generates a `.tex` file in `sample_data/demo_wisconsin_condo/output/`.

---

## Docker

```bash
docker-compose up --build
```

Open http://localhost:8000. Projects are persisted in the `./projects/` directory via a volume mount.

To enable PDF compilation inside the container, uncomment the LaTeX installation lines in the `Dockerfile`.

---

## User Flow

### 1. Create a Project

Navigate to **New Project** and enter:
- Association legal name
- State (e.g., WI)
- Association type (condominium, HOA, etc.)
- Meeting year

### 2. Upload Documents

Upload any of the following (the system will classify them automatically):

| Category | Files |
|---|---|
| **Governing** | Bylaws, Declaration/CC&Rs, Articles, Election Rules |
| **Financial** | Approved Budget, Year-End Financials, Reserve Study, Audit |
| **Operational** | Board Roster, Prior Minutes, Candidate Forms |
| **History** | Prior Annual Packet, Prior Notice, Prior Proxy |

Drag-and-drop or file picker supported. You can override the auto-classification for any file.

### 3. Review Missing Items

The system shows a prioritized list:
- **BLOCKER** — Packet cannot generate until resolved
- **REQUIRED** — Needed for a complete packet
- **CONDITIONAL** — Only needed if triggered (e.g., election with staggered terms)
- **RECOMMENDED** — Improves quality but optional

Each item explains what is missing, why it matters, and how to resolve it.

### 4. Meeting Setup

Enter any data not found in uploaded files:
- Meeting date, time, location
- Notice date
- Quorum threshold (if not in bylaws)
- Election details (seats up, term lengths, staggered terms)
- Financial figures (budget total, prior year-end net, reserve balance)
- Prior minutes status

### 5. Validate

The system checks:
- Notice period compliance (bylaw minimum vs. actual days)
- Quorum threshold identified
- Election consistency (staggered terms → seat map required)
- Proxy authorization
- Financial reporting obligation
- Board roster present

Results are shown as PASS / WARNING / BLOCKER.

### 6. Generate Packet

Click **Generate Packet** on the Export page. Options:
- **LaTeX only** (`.tex`) — Always available
- **Compile to PDF** — Requires LaTeX installation on the server

Download `.tex` and/or PDF when complete.

---

## Generated Packet Contents

The generated `.tex` file includes (configurable):

1. Cover Page
2. Official Annual Meeting Notice
3. Annual Meeting Agenda
4. Proxy Form
5. Board of Directors Nomination Form
6. Candidate Biographical Sketches
7. Financial Summary (Budget, Prior Year, YTD, Reserve Fund)
8. Prior Annual Meeting Minutes Status
9. Election Explanation & Procedures
10. Meeting Instructions for Unit Owners
11. Draft Annual Meeting Minutes Template

Each section is generated by logic, not static text:
- If no election → nomination form and election explanation are omitted
- If election required but staggered terms unclear → system blocks and explains
- If prior minutes unavailable → chair guidance note is included
- If proxy permitted → proxy form is tailored to the specific meeting

---

## State Jurisdiction Support

### Wisconsin (Full Implementation)

Located at `backend/jurisdictions/wi.yaml`. Covers:
- Wisconsin Condominium Ownership Act (Wis. Stat. ch. 703)
- Wisconsin Nonprofit Corporation Law (Wis. Stat. ch. 181)
- Default 10-day notice minimum (bylaws commonly increase to 15–30 days)
- Proxy rules and language defaults
- Organizational meeting requirement
- Financial reporting obligations
- Reserve fund guidance
- Document hierarchy (declaration over bylaws)

### Adding a New State

1. Create `backend/jurisdictions/xx.yaml` (where `xx` is the 2-letter state code, lowercase)
2. Follow the structure of `wi.yaml`
3. The system will detect it automatically

All legal content is explicitly authored in the YAML — the system does not infer or hallucinate law.

---

## Project Structure

```
EquusCapitalAdvisory/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app + HTML routes
│   │   ├── config.py
│   │   ├── models/
│   │   │   ├── association.py         # AssociationProfile model
│   │   │   ├── document.py            # Document types, ExtractedRule
│   │   │   ├── meeting.py             # MeetingProfile model
│   │   │   └── packet.py              # ProjectState, validation, financial, election models
│   │   ├── services/
│   │   │   ├── document_parser.py     # PDF/DOCX text extraction
│   │   │   ├── classifier.py          # Document type classifier
│   │   │   ├── rule_extractor.py      # Governance rule extraction engine
│   │   │   ├── missing_analyzer.py    # Missing-items analysis engine
│   │   │   ├── validator.py           # Compliance validation engine
│   │   │   ├── packet_generator.py    # LaTeX rendering pipeline
│   │   │   ├── jurisdiction_loader.py # State rules loader
│   │   │   └── project_store.py       # File-system persistence
│   │   └── routers/
│   │       ├── projects.py            # Project CRUD + setup API
│   │       ├── documents.py           # Upload + classify API
│   │       └── packets.py             # Generation + download API
│   ├── jurisdictions/
│   │   ├── wi.yaml                    # Wisconsin (fully implemented)
│   │   └── il.yaml                    # Illinois (scaffold)
│   ├── templates/
│   │   ├── html/                      # Jinja2 HTML frontend templates
│   │   └── latex/                     # LaTeX packet templates
│   │       ├── base.tex.j2
│   │       └── sections/
│   │           ├── cover.tex.j2
│   │           ├── notice.tex.j2
│   │           ├── agenda.tex.j2
│   │           ├── proxy.tex.j2
│   │           ├── candidate_form.tex.j2
│   │           ├── candidate_bios.tex.j2
│   │           ├── financial_summary.tex.j2
│   │           ├── minutes_status.tex.j2
│   │           ├── election_explanation.tex.j2
│   │           ├── meeting_instructions.tex.j2
│   │           └── minutes_template.tex.j2
│   └── static/                        # CSS/JS static files (auto-created)
├── projects/                          # Runtime project storage (auto-created)
├── sample_data/
│   └── demo_wisconsin_condo/
│       ├── bylaws_sample.txt          # Sample Wisconsin condo bylaws
│       ├── budget_2026.txt            # Sample 2026 budget
│       ├── board_roster.txt           # Sample board roster
│       └── demo_project_loader.py     # Demo project creator
├── tests/
│   ├── test_rule_extractor.py         # Rule engine unit tests (62 tests)
│   ├── test_missing_analyzer.py
│   ├── test_classifier.py
│   ├── test_validator.py
│   └── test_jurisdiction_loader.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## API Reference

All endpoints return JSON. The HTML frontend is served at `/`.

### Projects

| Method | Path | Description |
|---|---|---|
| GET | `/api/projects` | List all projects |
| POST | `/api/projects` | Create project |
| GET | `/api/projects/{id}` | Get full project state |
| PUT | `/api/projects/{id}/meeting` | Update meeting details |
| PUT | `/api/projects/{id}/financial` | Update financial data |
| PUT | `/api/projects/{id}/election` | Update election info |
| POST | `/api/projects/{id}/manual_entries` | Set manual override values |
| GET | `/api/projects/{id}/missing_items` | Run missing-items analysis |
| GET | `/api/projects/{id}/validation` | Run compliance validation |

### Documents

| Method | Path | Description |
|---|---|---|
| POST | `/api/projects/{id}/documents` | Upload and classify a document |
| GET | `/api/projects/{id}/documents` | List uploaded documents |
| PUT | `/api/projects/{id}/documents/{doc_id}/type` | Override document classification |
| DELETE | `/api/projects/{id}/documents/{doc_id}` | Remove a document |
| GET | `/api/projects/{id}/documents/rules` | View extracted rules |

### Packet Generation

| Method | Path | Description |
|---|---|---|
| POST | `/api/projects/{id}/packet/generate` | Generate LaTeX (+ optional PDF) |
| GET | `/api/projects/{id}/packet/download/tex` | Download `.tex` file |
| GET | `/api/projects/{id}/packet/download/pdf` | Download PDF |
| GET | `/api/projects/{id}/packet/preview` | Preview LaTeX source |

---

## Running Tests

```bash
pytest tests/ -v
```

62 tests covering rule extraction, missing-items analysis, document classification, compliance validation, and jurisdiction loading.

---

## Design Principles

- **Rule-driven, not template-based** — Every packet section is generated by logic derived from the actual governing documents and jurisdiction rules.
- **No hallucination** — State law content is explicitly authored in YAML files. The system only applies what has been written and reviewed.
- **Auditable** — Every extracted rule carries a source document ID, raw text snippet, and confidence score. Ambiguous rules are flagged, not silently resolved.
- **Association-agnostic** — No hardcoded association names, board sizes, or rule values. Works for any US community association.
- **Local-first** — All data stays on your machine. No cloud, no third-party API calls for document processing.

---

## Legal Disclaimer

This software generates documents based on governing-document text and jurisdiction-rule files authored by the user or system administrator. It does not provide legal advice. All generated packets should be reviewed by qualified legal counsel before distribution to unit owners. State law content in jurisdiction YAML files must be reviewed and kept current by counsel.
