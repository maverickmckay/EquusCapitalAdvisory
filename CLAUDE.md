# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Commands

```bash
# Development server
uvicorn backend.app.main:app --reload --port 8000

# Docker
docker-compose up --build

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_rule_extractor.py -v

# Run a single test
pytest tests/test_rule_extractor.py::TestNoticePeriod::test_not_less_than_15_days -v

# Load the demo project (creates output in sample_data/demo_wisconsin_condo/output/)
python -m sample_data.demo_wisconsin_condo.demo_project_loader
```

PDF compilation requires `pdflatex` or `latexmk` (TeX Live / MiKTeX) installed on the host. The Dockerfile has commented-out lines to add it.

---

## Architecture

**Data flow:**

```
Upload document
  → document_parser.py   (PDF/DOCX/TXT → raw text)
  → classifier.py        (DocumentType via regex signals + weights)
  → rule_extractor.py    (governance rules → ExtractedRule objects with source + confidence)
  → missing_analyzer.py  (what's missing + severity: BLOCKER/REQUIRED/CONDITIONAL/RECOMMENDED)
  → validator.py         (compliance: notice period, quorum, election consistency, proxy auth)
  → packet_generator.py  (Jinja2 → LaTeX .tex, optionally pdflatex → PDF)
```

**Persistence:** `project_store.py` writes one directory per project at `projects/{project_id}/` containing `project.json` (full `ProjectState`), `documents/`, and `output/`. The `projects/` directory is git-ignored.

**Jurisdiction overlay:** `backend/jurisdictions/wi.yaml` (full) and `il.yaml` (scaffold) provide state-law defaults. They are merged at validation time: document-extracted rules take priority over YAML defaults. Add a new state by creating `backend/jurisdictions/{code}.yaml`. All law content is explicitly authored — the system never infers statute text.

**Root model:** `ProjectState` in `backend/app/models/packet.py` contains `AssociationProfile`, `MeetingProfile`, `FinancialProfile`, `ElectionProfile`, `DocumentStatus`, plus dicts for `extracted_rules`, `jurisdiction_rules`, and `manual_entries`.

**Jinja2 custom filters** (registered in `packet_generator.py`): `tex_escape`, `format_date`, `format_currency`, `dict_get`.

**LaTeX templates** live at `backend/templates/latex/`. `base.tex.j2` is the master document; it `{% include %}`s the section files and controls which appear via `{% if sections.X %}` flags. LaTeX `\newcommand` macros containing `{#1}` must be wrapped in `{% raw %}...{% endraw %}` to prevent Jinja2 treating `{#` as a comment tag.

---

## Canonical Packet Template

Every generated packet must follow this exact structure and wording. Only the variables listed below may change. **Do not reword notices, proxies, or legal boilerplate** — only substitute variables.

### Document class and preamble

```latex
\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{setspace}
\usepackage{graphicx}
\usepackage{array}
\usepackage{longtable}
\usepackage{booktabs}
\usepackage[hidelinks]{hyperref}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage{multicol}
\usepackage{lastpage}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\setstretch{1.1}
```

### Section ordering

Cover Page → Packet Overview → Notice → Agenda → Proxy → Budget Summaries → Financial Statements → Minutes Template

Nomination form and candidate bios appear between Proxy and Budget Summaries only when `HAS_ELECTION=true`.

### Typography conventions

- `\strong{text}` → `\textbf{text}` (via `\newcommand`)
- `\money{amount}` → `\$amount` (via `\newcommand`)
- Fill lines: `\rule{Xin}{0.4pt}`
- Checkboxes: `\(\square\)`
- Financial tables: `booktabs` (`\toprule`, `\midrule`, `\bottomrule`)

### Variables Claude must treat as dynamic

**Association / meeting metadata**

| Variable | Example |
|---|---|
| `ASSOC_NAME_LONG` | `Legend Park Condominium Association` |
| `ASSOC_NAME_SHORT` | `Legend Park` |
| `ASSOC_CORPORATE_NAME` | `Legend Park Condominium Association, Inc.` |
| `MEETING_YEAR` | `2026` |
| `MEETING_DATE_LONG` | `Tuesday, May 19, 2026` |
| `MEETING_TIME` | `6{:}00 p.m.` |
| `REGISTRATION_TIME` | `5{:}45 p.m.` |
| `MEETING_LOCATION` | `Franklin Public Library` |
| `PACKET_PREPARED_DATE` | date on cover page |

**Manager / sender**

| Variable | Example |
|---|---|
| `MANAGER_NAME` | `Paul Koepnick, McKay` |
| `MANAGER_TITLE_LINE1` | `Senior Portfolio Manager` |
| `MANAGER_TITLE_LINE2` | `Capital Risk & Compliance, Mike & Mike's Management` |
| `MANAGER_EMAIL` | `pkoepnick@m3milwaukee.com` |

**Notice-specific**

| Variable | Example |
|---|---|
| `NOTICE_DEADLINE_DATETIME` | `5{:}00 p.m. on Friday, May 15, 2026` |
| `PROXY_DEADLINE_DATETIME` | same or different from above |

**Agenda flags**

- `HAS_ELECTION` (boolean)
- `PRIOR_MINUTES_YEAR`, `FINANCIAL_YE_YEAR_END`, `FINANCIAL_YTD_CUTOFF`

**Budget summary variables** — for each budget year (Y1 = prior, Y2 = current):

- Income: `BUDGET_Yn_CONDO_FEES`, `BUDGET_Yn_SALES_TRANSFER_FEE`, `BUDGET_Yn_INTEREST`, `BUDGET_Yn_LATE_FEES`, `BUDGET_Yn_RESERVE_XFER`, `BUDGET_Yn_TOTAL_INCOME`
- Maintenance: General Maintenance & Repairs, Roof/Chimney/Gutters, Gutter Cleaning, Landscape Maintenance, Tree Care, Landscape Improvements, Pest Control
- Contract/Admin: Insurance, Management, Snow Removal, Water & Sewer, Legal/Collection, Accounting, Postage/Copies, Taxes/Licenses/Permits, Banking Fees
- Missing budget categories default to `0.00`; the line stays in the table

**Financial statement variables**

- Prior year-end: `BS_PREV_OP_ACCOUNT`, `BS_PREV_RESERVE_ACCOUNT`, `BS_PREV_TOTAL_ASSETS`, `BS_PREV_PREPAID_FEES`, `BS_PREV_RETAINED_EARNINGS`, `BS_PREV_NET_INCOME`; `IS_PREV_TOTAL_INCOME`, `IS_PREV_TOTAL_EXPENSES`, `IS_PREV_NET_INCOME`
- Current YTD: same pattern prefixed `BS_CUR_` / `IS_CUR_YTD_` / `IS_CUR_MONTH_`

**Minutes template variables**: `MINUTES_MEETING_DATE_LONG`, `MINUTES_MEETING_TIME`, `MINUTES_MEETING_LOCATION`, `MINUTES_PRIOR_MINUTES_YEAR`, `MINUTES_HAS_ELECTION_SECTION`

### Error handling rule

If a required variable cannot be resolved from uploaded documents, the code must log the missing variable name and surface a clear message — e.g., `"Missing: MEETING_DATE_LONG. Please provide the meeting date."` — and must not fabricate numbers, dates, or text, and must not leave placeholders like "TBD".

### Financial consistency rule

Numbers in Budget Summary tables must reproduce the uploaded budget exactly (only formatting changes via `\money{}`). The variance-analysis narrative should reference the largest line-item changes by name and amount, not invented generalities.

---

## Key Patterns

**Rule extraction is deterministic, not LLM-based.** `rule_extractor.py` uses explicit regex patterns so a legal reviewer can audit what was matched. Every `ExtractedRule` carries `source_document_id`, `raw_text`, and `confidence` (HIGH/MEDIUM/LOW/UNVERIFIED).

**Jurisdiction overlay merge order:** document-extracted rule → `manual_entries` override → jurisdiction YAML default. Never the reverse.

**`MissingItemSeverity`:** BLOCKER = cannot generate; REQUIRED = complete packet; CONDITIONAL = only if a flag is true (e.g., `election_required`); RECOMMENDED = quality only.

**Adding a new state:** create `backend/jurisdictions/{code}.yaml` following `wi.yaml` structure. The loader auto-detects it. All statute text must be explicitly written — do not infer.

**Adding a new rule type:** add pattern to `rule_extractor.py`, add function `extract_my_rule(text, doc_id) -> List[ExtractedRule]`, call it from `extract_rules()`, add tests in `test_rule_extractor.py`.

**Adding a new LaTeX section:** create `backend/templates/latex/sections/my_section.tex.j2`, add `{% if sections.my_section %}` include to `base.tex.j2`, add flag to `PacketSections`, populate in `packet_generator.py` context builder.
