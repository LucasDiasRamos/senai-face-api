from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.config import UPLOAD_DIR
from app.database import create_person, delete_person, get_person, list_people, save_embedding, update_person
from app.services.log_service import register_log


def create_new_person(person_id, name, unit_id=None, role=None, unit=None):
    try:
        create_person(person_id, name, unit_id=unit_id, role=role, unit=unit)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        if "UNIQUE" in str(error).upper():
            raise HTTPException(status_code=409, detail="person_id já cadastrado")
        raise

    register_log("CREATE_PERSON", person_id, f"Pessoa cadastrada: {name}")
    return get_person(person_id)


def get_people():
    return list_people()


def update_existing_person(person_id, name, unit_id=None, role=None, unit=None):
    require_person(person_id)
    try:
        person = update_person(person_id, name, unit_id=unit_id, role=role, unit=unit)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    register_log("UPDATE_PERSON", person_id, f"Pessoa atualizada: {name}")
    return person


def require_person(person_id):
    person = get_person(person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada")
    return person


async def add_person_photo(person_id, image: UploadFile, face_engine):
    person = require_person(person_id)
    image_bytes = await image.read()

    try:
        embedding = face_engine.get_embedding(image_bytes)
    except ValueError as error:
        register_log("FACE_ERROR", person_id, str(error))
        raise HTTPException(status_code=400, detail=str(error))

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    extension = Path(image.filename or "foto.jpg").suffix.lower() or ".jpg"
    filename = f"{person_id}-{uuid4().hex}{extension}"
    image_path = UPLOAD_DIR / filename
    image_path.write_bytes(image_bytes)

    save_embedding(person_id, embedding, str(image_path))
    register_log("UPLOAD_PHOTO", person_id, "Foto cadastrada e embedding gerado")
    return person


def delete_existing_person(person_id):
    result = delete_person(person_id)
    if not result:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada")

    for image_path in result["image_paths"]:
        try:
            Path(image_path).unlink(missing_ok=True)
        except OSError:
            pass

    person = result["person"]
    register_log("DELETE_PERSON", None, f"Pessoa removida: {person['name']} ({person['person_id']})")
    return result
