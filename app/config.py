import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "faces.db"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "data" / "uploads")))

FACE_CTX_ID = int(os.getenv("FACE_CTX_ID", "-1"))
FACE_HIGH_THRESHOLD = float(os.getenv("FACE_HIGH_THRESHOLD", "0.70"))
FACE_MEDIUM_THRESHOLD = float(os.getenv("FACE_MEDIUM_THRESHOLD", "0.55"))

FORMS_IMPORT_PREFIX = os.getenv("FORMS_IMPORT_PREFIX", "JP2026")
FORMS_IMPORT_MAX_IMAGE_MB = int(os.getenv("FORMS_IMPORT_MAX_IMAGE_MB", "10"))
FORMS_IMPORT_MAX_FILES = int(os.getenv("FORMS_IMPORT_MAX_FILES", "2000"))
