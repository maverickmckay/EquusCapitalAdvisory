"""
HOA Annual Meeting Packet Generator — FastAPI application.

Provides both a REST API and a server-rendered HTML frontend.
"""
from __future__ import annotations
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .config import APP_TITLE, APP_VERSION
from .routers import projects, documents, packets

BASE_DIR = Path(__file__).parent.parent

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="Generate professional HOA annual meeting packets from governing documents.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# HTML templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates" / "html"))

# Include API routers
app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(packets.router)


# ---------------------------------------------------------------------------
# HTML Frontend routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    from .services.project_store import list_projects
    projects_list = list_projects()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "projects": projects_list,
        "app_title": APP_TITLE,
    })


@app.get("/projects/new", response_class=HTMLResponse)
async def new_project_page(request: Request):
    from .services.jurisdiction_loader import list_available_jurisdictions
    jurisdictions = list_available_jurisdictions()
    return templates.TemplateResponse("new_project.html", {
        "request": request,
        "jurisdictions": jurisdictions,
        "app_title": APP_TITLE,
    })


@app.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_detail(request: Request, project_id: str):
    from .services.project_store import load_project
    from .services.missing_analyzer import analyze_missing_items, summarize_missing
    from .services.validator import run_validation, validation_summary

    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    state.document_status = analyze_missing_items(state)
    validation_results = run_validation(state)
    vsummary = validation_summary(validation_results)
    missing_summary = summarize_missing(state)

    assoc = state.association
    if hasattr(assoc, "dict"):
        assoc_dict = assoc.dict()
    else:
        assoc_dict = assoc or {}

    return templates.TemplateResponse("project.html", {
        "request": request,
        "project": state.dict(),
        "association": assoc_dict,
        "missing_summary": missing_summary,
        "validation": vsummary,
        "validation_results": [r.dict() for r in validation_results],
        "app_title": APP_TITLE,
        "doc_types": [dt.value for dt in __import__("app.models.document", fromlist=["DocumentType"]).DocumentType],
    })


@app.get("/projects/{project_id}/upload", response_class=HTMLResponse)
async def upload_page(request: Request, project_id: str):
    from .services.project_store import load_project
    from .models.document import DocumentType

    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    assoc = state.association
    assoc_dict = assoc.dict() if hasattr(assoc, "dict") else (assoc or {})

    return templates.TemplateResponse("upload.html", {
        "request": request,
        "project": state.dict(),
        "association": assoc_dict,
        "doc_types": [(dt.value, dt.value.replace("_", " ").title()) for dt in DocumentType],
        "uploaded_docs": [d.dict() for d in state.document_status.uploaded_docs],
        "app_title": APP_TITLE,
    })


@app.get("/projects/{project_id}/setup", response_class=HTMLResponse)
async def setup_page(request: Request, project_id: str):
    from .services.project_store import load_project
    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    assoc = state.association
    assoc_dict = assoc.dict() if hasattr(assoc, "dict") else (assoc or {})

    return templates.TemplateResponse("setup.html", {
        "request": request,
        "project": state.dict(),
        "association": assoc_dict,
        "meeting": state.meeting.dict(),
        "financial": state.financial.dict(),
        "election": state.election.dict(),
        "app_title": APP_TITLE,
    })


@app.get("/projects/{project_id}/export", response_class=HTMLResponse)
async def export_page(request: Request, project_id: str):
    from .services.project_store import load_project
    from .services.missing_analyzer import analyze_missing_items, summarize_missing
    from .services.validator import run_validation, validation_summary

    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    state.document_status = analyze_missing_items(state)
    validation_results = run_validation(state)
    vsummary = validation_summary(validation_results)
    missing_summary = summarize_missing(state)

    assoc = state.association
    assoc_dict = assoc.dict() if hasattr(assoc, "dict") else (assoc or {})

    return templates.TemplateResponse("export.html", {
        "request": request,
        "project": state.dict(),
        "association": assoc_dict,
        "missing_summary": missing_summary,
        "validation": vsummary,
        "has_tex": bool(state.generated_tex_path),
        "has_pdf": bool(state.generated_pdf_path),
        "last_generated": state.last_generated_at.isoformat() if state.last_generated_at else None,
        "app_title": APP_TITLE,
    })


@app.get("/health")
def health():
    return {"status": "ok", "app": APP_TITLE, "version": APP_VERSION}
