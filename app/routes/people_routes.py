from fastapi import APIRouter, File, Form, Request, UploadFile

from app.services.people_service import (
    add_person_photo,
    create_new_person,
    delete_existing_person,
    get_people,
    require_person,
    update_existing_person,
)


router = APIRouter()


@router.post("/people")
async def create_person_route(
    person_id: str = Form(...),
    name: str = Form(...),
    unit_id: int | None = Form(None),
    unit: str | None = Form(None),
    role: str | None = Form(None),
):
    person = create_new_person(person_id, name, unit_id=unit_id, role=role, unit=unit)
    return {
        "success": True,
        "person_id": person["person_id"],
        "name": person["name"],
        "unit_id": person.get("unit_id"),
        "unit": person.get("unit"),
        "message": "Pessoa cadastrada com sucesso",
    }


@router.get("/people")
def list_people_route(
    unit_id: int | None = None,
    search: str | None = None,
):
    return {
        "success": True,
        "people": get_people(
            unit_id=unit_id,
            search=search,
        ),
    }


@router.get("/people/{person_id}")
def get_person_route(person_id: str):
    return {
        "success": True,
        "person": require_person(person_id),
    }


@router.put("/people/{person_id}")
async def update_person_route(
    person_id: str,
    name: str = Form(...),
    unit_id: int | None = Form(None),
    unit: str | None = Form(None),
    role: str | None = Form(None),
):
    person = update_existing_person(person_id, name, unit_id=unit_id, role=role, unit=unit)
    return {
        "success": True,
        "person": person,
        "message": "Pessoa atualizada com sucesso",
    }


@router.delete("/people/{person_id}")
def delete_person_route(person_id: str):
    result = delete_existing_person(person_id)
    return {
        "success": True,
        "person": result["person"],
        "deleted_checkins": result["deleted_checkins"],
        "deleted_embeddings": result["deleted_embeddings"],
        "deleted_logs": result["deleted_logs"],
        "message": "Pessoa removida com sucesso",
    }


@router.post("/people/{person_id}/photo")
async def upload_photo_route(
    request: Request,
    person_id: str,
    image: UploadFile = File(...),
):
    await add_person_photo(person_id, image, request.app.state.face_engine)
    return {
        "success": True,
        "person_id": person_id,
        "message": "Foto cadastrada e embedding gerado com sucesso",
    }
