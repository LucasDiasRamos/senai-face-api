from fastapi import UploadFile

from app.config import FACE_HIGH_THRESHOLD
from app.database import create_checkin, delete_checkin, get_existing_checkin, list_checkins
from app.services.log_service import register_log
from app.services.people_service import require_person
from app.services.recognition_service import recognize_image
from app.services.units_service import require_unit


def _record_checkin(person, method, confidence=None):
    if person.get("unit_id") is not None and not person.get("unit"):
        unit = require_unit(person["unit_id"])
        person["unit"] = unit["name"]

    existing = get_existing_checkin(person["person_id"])
    if existing:
        create_checkin(
            person["person_id"],
            person["name"],
            method,
            confidence,
            already_checked_in=True,
            unit_id=person.get("unit_id"),
            unit=person.get("unit"),
        )
        register_log("DUPLICATE_CHECKIN", person["person_id"], "Pessoa já estava credenciada")
        return {
            "checked_in": False,
            "already_checked_in": True,
            "person_id": person["person_id"],
            "name": person["name"],
            "unit_id": person.get("unit_id"),
            "unit": person.get("unit"),
            "confidence": confidence,
            "message": "Pessoa já estava credenciada",
        }

    create_checkin(
        person["person_id"],
        person["name"],
        method,
        confidence,
        already_checked_in=False,
        unit_id=person.get("unit_id"),
        unit=person.get("unit"),
    )
    register_log("CHECKIN", person["person_id"], f"Check-in via {method}")
    return {
        "checked_in": True,
        "already_checked_in": False,
        "person_id": person["person_id"],
        "name": person["name"],
        "unit_id": person.get("unit_id"),
        "unit": person.get("unit"),
        "confidence": confidence,
        "message": "Credenciamento realizado com sucesso" if method == "face" else "Check-in manual realizado com sucesso",
    }


async def facial_checkin(image: UploadFile, face_engine, person_id, unit_id=None):
    expected_person = require_person(person_id)
    if unit_id is not None:
        require_unit(unit_id)

    recognition = await recognize_image(image, face_engine)
    confidence = recognition.get("confidence")

    if not recognition.get("recognized") or confidence is None or confidence < FACE_HIGH_THRESHOLD:
        register_log("LOW_CONFIDENCE", recognition.get("person_id"), "Check-in facial sem confiança suficiente")
        return {
            "recognized": False,
            "checked_in": False,
            "possible_person": recognition.get("name"),
            "confidence": confidence,
            "message": "Pessoa não reconhecida com confiança suficiente",
        }

    if recognition["person_id"] != expected_person["person_id"]:
        register_log(
            "FACE_MISMATCH",
            expected_person["person_id"],
            f"Face reconhecida para {recognition['person_id']} mas o check-in solicitado era para {expected_person['person_id']}",
        )
        return {
            "recognized": False,
            "checked_in": False,
            "person_id": expected_person["person_id"],
            "name": expected_person["name"],
            "unit_id": unit_id if unit_id is not None else expected_person.get("unit_id"),
            "unit": None if unit_id is not None else expected_person.get("unit"),
            "role": expected_person.get("role"),
            "confidence": confidence,
            "message": "A face enviada nao corresponde a pessoa selecionada",
        }

    person = {
        "person_id": expected_person["person_id"],
        "name": expected_person["name"],
        "unit_id": unit_id if unit_id is not None else expected_person.get("unit_id"),
        "unit": None if unit_id is not None else expected_person.get("unit"),
        "role": expected_person.get("role"),
    }
    result = _record_checkin(person, "face", confidence)
    return {
        "recognized": True,
        **result,
        "role": expected_person.get("role"),
    }


def manual_checkin(person_id, unit_id=None):
    person = require_person(person_id)
    if unit_id is not None:
        unit = require_unit(unit_id)
        person["unit_id"] = unit_id
        person["unit"] = unit["name"]
    result = _record_checkin(person, "manual")
    return {
        "success": True,
        **result,
    }


def get_checkins():
    return list_checkins()


def remove_checkin(checkin_id):
    checkin = delete_checkin(checkin_id)
    if checkin:
        register_log("DELETE_CHECKIN", checkin["person_id"], f"Check-in removido: #{checkin_id}")
    return checkin
