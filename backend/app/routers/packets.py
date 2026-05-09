"""
Packet generation routes.
"""
from __future__ import annotations
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..services.project_store import load_project, save_project
from ..services.missing_analyzer import analyze_missing_items
from ..services.validator import run_validation, validation_summary
from ..services.packet_generator import generate_packet

router = APIRouter(prefix="/api/projects/{project_id}/packet", tags=["packet"])


@router.post("/generate")
def generate(project_id: str, compile_pdf: bool = False, force: bool = False):
    """
    Generate the LaTeX (and optionally PDF) packet for this project.

    Set force=True to bypass blocker warnings.
    Set compile_pdf=True to attempt PDF compilation (requires LaTeX installation).
    """
    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    # Re-run analysis
    state.document_status = analyze_missing_items(state)
    validation_results = run_validation(state)
    vsummary = validation_summary(validation_results)

    if not force and not vsummary["ready_to_generate"]:
        return {
            "success": False,
            "blocked": True,
            "message": "Packet generation blocked by validation errors. Review the validation report or use force=true.",
            "validation": vsummary,
        }

    output_dir = Path(__file__).parent.parent.parent.parent / "projects" / project_id / "output"
    result = generate_packet(state, output_dir=output_dir, compile_pdf=compile_pdf)

    if result["success"]:
        state.generated_tex_path = result["tex_path"]
        state.generated_pdf_path = result["pdf_path"]
        from datetime import datetime
        state.last_generated_at = datetime.utcnow()
        save_project(state)

    return {
        "success": result["success"],
        "tex_path": result["tex_path"],
        "pdf_path": result["pdf_path"],
        "errors": result["errors"],
        "validation_warnings": vsummary.get("warning_count", 0),
    }


@router.get("/download/tex")
def download_tex(project_id: str):
    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")
    if not state.generated_tex_path:
        raise HTTPException(status_code=404, detail="No .tex file generated yet. Call /generate first.")

    path = Path(state.generated_tex_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Generated .tex file not found on disk.")

    filename = f"{state.project_id}_annual_packet.tex"
    return FileResponse(path=str(path), media_type="text/plain", filename=filename)


@router.get("/download/pdf")
def download_pdf(project_id: str):
    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")
    if not state.generated_pdf_path:
        raise HTTPException(status_code=404, detail="No PDF generated yet. Call /generate?compile_pdf=true first.")

    path = Path(state.generated_pdf_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Generated PDF not found on disk.")

    filename = f"{state.project_id}_annual_packet.pdf"
    return FileResponse(path=str(path), media_type="application/pdf", filename=filename)


@router.get("/preview")
def preview_packet(project_id: str):
    """Return the generated .tex content as text for browser preview."""
    state = load_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")
    if not state.generated_tex_path:
        raise HTTPException(status_code=404, detail="No .tex file generated yet.")

    path = Path(state.generated_tex_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=".tex file not found on disk.")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    return {"content": content, "filename": path.name}
