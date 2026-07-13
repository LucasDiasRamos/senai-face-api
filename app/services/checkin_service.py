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


async def facial_checkin(
    image: UploadFile,
    face_engine,
    source: str | None = None,
    robot_id: str | None = None,
):
    recognition = await recognize_image(image, face_engine)
    status = recognition.get("status")
    confidence = recognition.get("confidence")
    request_context = f"source={source or 'unknown'}; robot_id={robot_id or 'unknown'}"

    if status == "no_face":
        register_log("NO_FACE_CHECKIN", None, request_context)
        return {
            "status": "no_face",
            "recognized": False,
            "checked_in": False,
            "already_checked_in": False,
            "face_count": 0,
            "confidence": None,
            "message": recognition.get("message"),
        }

    if status == "multiple_faces":
        face_count = recognition.get("face_count", 2)
        register_log("MULTIPLE_FACES_CHECKIN", None, f"{request_context}; face_count={face_count}")
        return {
            "status": "multiple_faces",
            "recognized": False,
            "checked_in": False,
            "already_checked_in": False,
            "face_count": face_count,
            "confidence": None,
            "message": recognition.get("message"),
        }

    if not recognition.get("recognized") or confidence is None or confidence < FACE_HIGH_THRESHOLD:
        person_id = recognition.get("person_id")
        register_log("LOW_CONFIDENCE", person_id, f"{request_context}; confidence={confidence}")
        is_low_confidence = recognition.get("needs_confirmation") or status == "low_confidence"
        return {
            "status": "low_confidence" if is_low_confidence else "not_recognized",
            "recognized": False,
            "checked_in": False,
            "already_checked_in": False,
            "face_count": recognition.get("face_count", 1),
            "possible_person": recognition.get("name"),
            "confidence": confidence,
            "message": (
                "Pessoa possivelmente reconhecida, mas sem confiança suficiente para o credenciamento automático"
                if is_low_confidence
                else "Pessoa não reconhecida com confiança suficiente"
            ),
        }

    person = require_person(recognition["person_id"])
    result = _record_checkin(person, "face", confidence)
    final_status = "already_checked_in" if result.get("already_checked_in") else "recognized"
    register_log(
        "FACE_CHECKIN_RESULT",
        person["person_id"],
        f"{request_context}; status={final_status}; confidence={confidence}",
    )
    return {
        "status": final_status,
        "recognized": True,
        "face_count": 1,
        **result,
        "role": person.get("role"),
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
