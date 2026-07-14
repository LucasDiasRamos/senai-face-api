import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.services.forms_import_service import import_forms_people


router = APIRouter()


def _validate_upload(upload: UploadFile, expected_extension: str, label: str):
    extension = Path(upload.filename or "").suffix.lower()
    if extension != expected_extension:
        raise HTTPException(status_code=400, detail=f"{label} deve ser um arquivo {expected_extension}.")


async def _save_temp_upload(upload: UploadFile, suffix: str) -> Path:
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    path = Path(handle.name)
    try:
        with handle:
            while chunk := await upload.read(1024 * 1024):
                handle.write(chunk)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


@router.post("/imports/forms")
async def import_forms_route(
    request: Request,
    spreadsheet: UploadFile = File(...),
    photos: UploadFile = File(...),
):
    _validate_upload(spreadsheet, ".xlsx", "A planilha")
    _validate_upload(photos, ".zip", "O arquivo de fotos")

    spreadsheet_path = None
    photos_path = None
    try:
        spreadsheet_path = await _save_temp_upload(spreadsheet, ".xlsx")
        photos_path = await _save_temp_upload(photos, ".zip")
        report = import_forms_people(
            excel_path=spreadsheet_path,
            zip_path=photos_path,
            face_engine=request.app.state.face_engine,
        )
    finally:
        if spreadsheet_path:
            spreadsheet_path.unlink(missing_ok=True)
        if photos_path:
            photos_path.unlink(missing_ok=True)

    return {
        "success": True,
        "summary": {
            "total_rows": report["total_rows"],
            "imported": report["imported"],
            "photo_completed": report["photo_completed"],
            "ignored": report["ignored"],
            "errors_count": report["errors_count"],
        },
        "errors": report["errors"],
    }
