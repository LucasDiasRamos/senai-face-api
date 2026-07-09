from fastapi import HTTPException

from app.database import get_unit, list_units


def get_units():
    return list_units()


def require_unit(unit_id):
    unit = get_unit(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unidade não encontrada")
    return unit
