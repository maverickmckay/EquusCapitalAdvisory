"""
LaTeX packet generator.

Renders the Jinja2 LaTeX templates against a fully-populated
ProjectState and writes the .tex file.  Optionally invokes
pdflatex/latexmk to compile to PDF.
"""
from __future__ import annotations
import os
import re
import subprocess
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape, Undefined

from ..models.packet import ProjectState

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
PROJECTS_DIR = Path(__file__).parent.parent.parent.parent / "projects"


# ---------------------------------------------------------------------------
# Jinja2 filters
# ---------------------------------------------------------------------------

def _tex_escape(value) -> str:
    """Escape special LaTeX characters in a string."""
    if value is None or isinstance(value, Undefined):
        return ""
    s = str(value)
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&",  r"\&"),
        ("%",  r"\%"),
        ("$",  r"\$"),
        ("#",  r"\#"),
        ("_",  r"\_"),
        ("{",  r"\{"),
        ("}",  r"\}"),
        ("~",  r"\textasciitilde{}"),
        ("^",  r"\textasciicircum{}"),
    ]
    for char, replacement in replacements:
        s = s.replace(char, replacement)
    return s


def _format_date(value) -> str:
    if value is None or isinstance(value, Undefined):
        return "________________"
    if isinstance(value, str):
        return value
    if isinstance(value, date):
        return value.strftime("%B %d, %Y")
    return str(value)


def _format_currency(value) -> str:
    if value is None or isinstance(value, Undefined):
        return "0.00"
    try:
        return f"{float(value):,.2f}"
    except (ValueError, TypeError):
        return str(value)


def _dict_get(d, key, default=""):
    if d is None or isinstance(d, Undefined):
        return default
    if isinstance(d, dict):
        return d.get(key, default)
    return default


def _build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
    )
    env.filters["tex_escape"] = _tex_escape
    env.filters["format_date"] = _format_date
    env.filters["format_currency"] = _format_currency
    env.globals["dict_get"] = _dict_get
    return env


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

def _build_context(state: ProjectState) -> dict:
    assoc = state.association or {}
    if hasattr(assoc, "dict"):
        assoc_dict = assoc.dict()
    elif isinstance(assoc, dict):
        assoc_dict = assoc
    else:
        assoc_dict = {}

    has_prior_minutes = any(
        d.document_type == "prior_annual_minutes"
        for d in state.document_status.uploaded_docs
    )

    notice_compliance_note = False
    if state.meeting.notice_date and state.meeting.meeting_date:
        notice_compliance_note = True

    return {
        # Top-level
        "association_name": assoc_dict.get("association_name", "Association Name"),
        "meeting_year": state.association.meeting_year if state.association else 2026,
        "generated_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "include_toc": state.packet_sections.table_of_contents,

        # Sub-objects
        "association": assoc_dict,
        "meeting": state.meeting,
        "financial": state.financial,
        "election": state.election,
        "sections": state.packet_sections,
        "jx": state.jurisdiction_rules,
        "manual_entries": state.manual_entries,

        # Management info
        "management_company": assoc_dict.get("management_company", ""),
        "management_contact": assoc_dict.get("management_contact", ""),
        "management_email": assoc_dict.get("management_email", ""),
        "management_phone": assoc_dict.get("management_phone", ""),

        # Flags
        "has_prior_minutes": has_prior_minutes,
        "notice_compliance_note": notice_compliance_note,
        "custom_proxy_language": state.manual_entries.get("custom_proxy_language", ""),
    }


# ---------------------------------------------------------------------------
# Main generation function
# ---------------------------------------------------------------------------

def generate_packet(
    state: ProjectState,
    output_dir: Optional[Path] = None,
    compile_pdf: bool = False,
) -> dict:
    """
    Render the LaTeX packet for the given project state.

    Returns a dict with:
      - tex_path: absolute path to the generated .tex file
      - pdf_path: absolute path to PDF (if compiled), else None
      - success: bool
      - errors: list of error messages
    """
    errors = []
    tex_path = None
    pdf_path = None

    # Determine output directory
    if output_dir is None:
        proj_dir = PROJECTS_DIR / state.project_id / "output"
    else:
        proj_dir = output_dir
    proj_dir.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", state.project_id)
    tex_filename = f"{safe_name}_annual_packet.tex"
    tex_path = proj_dir / tex_filename

    try:
        env = _build_env()
        template = env.get_template("latex/base.tex.j2")
        context = _build_context(state)
        rendered = template.render(**context)

        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(rendered)

    except Exception as e:
        errors.append(f"LaTeX rendering error: {e}")
        return {"tex_path": None, "pdf_path": None, "success": False, "errors": errors}

    # Optional PDF compilation
    if compile_pdf:
        pdf_result = _compile_pdf(tex_path, proj_dir)
        if pdf_result["success"]:
            pdf_path = pdf_result["pdf_path"]
        else:
            errors.extend(pdf_result["errors"])

    return {
        "tex_path": str(tex_path),
        "pdf_path": str(pdf_path) if pdf_path else None,
        "success": True,
        "errors": errors,
    }


def _compile_pdf(tex_path: Path, output_dir: Path) -> dict:
    """Attempt to compile a .tex file to PDF using latexmk or pdflatex."""
    errors = []

    # Try latexmk first (preferred)
    compiler = _find_compiler()
    if not compiler:
        return {
            "success": False,
            "pdf_path": None,
            "errors": ["No LaTeX compiler found. Install texlive or miktex to enable PDF compilation."],
        }

    try:
        if compiler == "latexmk":
            cmd = [
                "latexmk",
                "-pdf",
                "-interaction=nonstopmode",
                f"-output-directory={output_dir}",
                str(tex_path),
            ]
        else:
            cmd = [
                "pdflatex",
                "-interaction=nonstopmode",
                f"-output-directory={output_dir}",
                str(tex_path),
            ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(output_dir),
            timeout=120,
        )

        # Run twice for cross-references (pdflatex only)
        if compiler == "pdflatex":
            subprocess.run(cmd, capture_output=True, text=True, cwd=str(output_dir), timeout=120)

        pdf_path = output_dir / (tex_path.stem + ".pdf")
        if pdf_path.exists():
            return {"success": True, "pdf_path": pdf_path, "errors": []}

        errors.append(f"PDF not produced. Compiler output:\n{result.stdout[-2000:]}")
        return {"success": False, "pdf_path": None, "errors": errors}

    except subprocess.TimeoutExpired:
        return {"success": False, "pdf_path": None, "errors": ["LaTeX compilation timed out."]}
    except Exception as e:
        return {"success": False, "pdf_path": None, "errors": [f"Compilation error: {e}"]}


def _find_compiler() -> Optional[str]:
    for compiler in ("latexmk", "pdflatex"):
        if shutil.which(compiler):
            return compiler
    return None
