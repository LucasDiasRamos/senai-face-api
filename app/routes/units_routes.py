from fastapi import APIRouter

from app.services.units_service import get_units


router = APIRouter()


@router.get("/units")
def list_units_route():
    return {
        "success": True,
        "units": get_units(),
    }
