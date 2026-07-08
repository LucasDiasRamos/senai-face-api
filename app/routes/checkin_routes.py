import csv
import io

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.database import dashboard_stats
from app.services.checkin_service import facial_checkin, get_checkins, manual_checkin, remove_checkin
from app.services.log_service import get_logs


router = APIRouter()


@router.post("/checkin-face")
async def checkin_face_route(request: Request, image: UploadFile = File(...)):
    return await facial_checkin(image, request.app.state.face_engine)


@router.post("/checkin-manual")
def checkin_manual_route(person_id: str = Form(...)):
    return manual_checkin(person_id)


@router.get("/checkins")
def list_checkins_route():
    return {
        "success": True,
        "checkins": get_checkins(),
    }


@router.delete("/checkins/{checkin_id}")
def delete_checkin_route(checkin_id: int):
    checkin = remove_checkin(checkin_id)
    if not checkin:
        raise HTTPException(status_code=404, detail="Check-in não encontrado")
    return {
        "success": True,
        "checkin": checkin,
        "message": "Check-in removido com sucesso",
    }


@router.get("/checkins/export")
def export_checkins_route():
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["person_id", "name", "method", "confidence", "already_checked_in", "checked_in_at"],
    )
    writer.writeheader()
    for row in get_checkins():
        writer.writerow({
            "person_id": row["person_id"],
            "name": row["name"],
            "method": row["method"],
            "confidence": row["confidence"] if row["confidence"] is not None else "",
            "already_checked_in": row["already_checked_in"],
            "checked_in_at": row["checked_in_at"],
        })

    output.seek(0)
    headers = {"Content-Disposition": "attachment; filename=credenciamentos.csv"}
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)


@router.get("/dashboard")
def dashboard_route():
    return {
        "success": True,
        "stats": dashboard_stats(),
        "latest_checkins": get_checkins()[:10],
        "latest_logs": get_logs(limit=10),
    }
