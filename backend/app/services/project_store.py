"""
Project persistence layer.

Projects are stored as JSON on disk under /projects/<project_id>/.
This is intentionally simple — no database required for local use.
"""
from __future__ import annotations
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from ..models.packet import ProjectState

PROJECTS_DIR = Path(__file__).parent.parent.parent.parent / "projects"


def _project_dir(project_id: str) -> Path:
    return PROJECTS_DIR / project_id


def _state_path(project_id: str) -> Path:
    return _project_dir(project_id) / "state.json"


def _uploads_dir(project_id: str) -> Path:
    return _project_dir(project_id) / "uploads"


def save_project(state: ProjectState) -> None:
    d = _project_dir(state.project_id)
    d.mkdir(parents=True, exist_ok=True)
    _uploads_dir(state.project_id).mkdir(exist_ok=True)
    (d / "output").mkdir(exist_ok=True)

    state.updated_at = datetime.utcnow()
    with open(_state_path(state.project_id), "w", encoding="utf-8") as f:
        f.write(state.json(indent=2))


def load_project(project_id: str) -> Optional[ProjectState]:
    path = _state_path(project_id)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ProjectState(**data)


def list_projects() -> List[dict]:
    if not PROJECTS_DIR.exists():
        return []
    projects = []
    for d in sorted(PROJECTS_DIR.iterdir()):
        if not d.is_dir():
            continue
        state_file = d / "state.json"
        if not state_file.exists():
            continue
        try:
            with open(state_file, "r") as f:
                data = json.load(f)
            projects.append({
                "project_id": data.get("project_id", d.name),
                "project_name": data.get("project_name", "Unknown"),
                "created_at": data.get("created_at", ""),
                "updated_at": data.get("updated_at", ""),
                "association_name": (data.get("association") or {}).get("association_name", ""),
                "state": (data.get("association") or {}).get("state", ""),
                "meeting_year": (data.get("association") or {}).get("meeting_year", ""),
                "has_tex": bool(data.get("generated_tex_path")),
                "has_pdf": bool(data.get("generated_pdf_path")),
            })
        except Exception:
            continue
    return projects


def delete_project(project_id: str) -> bool:
    d = _project_dir(project_id)
    if not d.exists():
        return False
    shutil.rmtree(d)
    return True


def save_upload(project_id: str, filename: str, content: bytes) -> Path:
    uploads = _uploads_dir(project_id)
    uploads.mkdir(parents=True, exist_ok=True)
    dest = uploads / filename
    with open(dest, "wb") as f:
        f.write(content)
    return dest


def get_upload_path(project_id: str, filename: str) -> Optional[Path]:
    path = _uploads_dir(project_id) / filename
    return path if path.exists() else None
