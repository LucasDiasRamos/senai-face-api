from fastapi import APIRouter

from app.services.log_service import get_logs


router = APIRouter()


@router.get("/logs")
def list_logs_route():
    return {
        "success": True,
        "logs": get_logs(),
    }
