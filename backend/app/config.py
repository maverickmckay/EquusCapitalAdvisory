from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
JURISDICTIONS_DIR = BASE_DIR / "jurisdictions"
PROJECTS_DIR = BASE_DIR.parent / "projects"

APP_TITLE = "HOA Annual Meeting Packet Generator"
APP_VERSION = "1.0.0"
MAX_UPLOAD_MB = 50
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".csv", ".md"}
