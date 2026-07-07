from fastapi import UploadFile

from app.config import FACE_HIGH_THRESHOLD
from app.database import create_checkin, get_existing_checkin, list_checkins
from app.services.log_service import register_log
from app.services.people_service import require_person
from app.services.recognition_service import recognize_image


def _record_checkin(person, method, confidence=None):
    existing = get_existing_checkin(person["person_id"])
    if existing:
        create_checkin(
            person["person_id"],
            person["name"],
            method,
            confidence,
            already_checked_in=True,
        )
        register_log("DUPLICATE_CHECKIN", person["person_id"], "Pessoa já estava credenciada")
        return {
            "checked_in": False,
            "already_checked_in": True,
            "person_id": person["person_id"],
            "name": person["name"],
            "confidence": confidence,
            "message": "Pessoa já estava credenciada",
        }

    create_checkin(
        person["person_id"],
        person["name"],
        method,
        confidence,
        already_checked_in=False,
    )
    register_log("CHECKIN", person["person_id"], f"Check-in via {method}")
    return {
        "checked_in": True,
        "already_checked_in": False,
        "person_id": person["person_id"],
        "name": person["name"],
        "confidence": confidence,
        "message": "Credenciamento realizado com sucesso" if method == "face" else "Check-in manual realizado com sucesso",
    }


async def facial_checkin(image: UploadFile, face_engine):
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

    person = {
        "person_id": recognition["person_id"],
        "name": recognition["name"],
    }
    result = _record_checkin(person, "face", confidence)
    return {
        "recognized": True,
        **result,
    }


def manual_checkin(person_id):
    person = require_person(person_id)
    result = _record_checkin(person, "manual")
    return {
        "success": True,
        **result,
    }


def get_checkins():
    return list_checkins()
