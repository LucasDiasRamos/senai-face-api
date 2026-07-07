from fastapi import APIRouter, File, Form, Request, UploadFile

from app.services.people_service import add_person_photo, create_new_person, get_people, require_person


router = APIRouter()


@router.post("/people")
async def create_person_route(
    person_id: str = Form(...),
    name: str = Form(...),
    unit: str | None = Form(None),
    role: str | None = Form(None),
):
    person = create_new_person(person_id, name, unit, role)
    return {
        "success": True,
        "person_id": person["person_id"],
        "name": person["name"],
        "message": "Pessoa cadastrada com sucesso",
    }


@router.get("/people")
def list_people_route():
    return {
        "success": True,
        "people": get_people(),
    }


@router.get("/people/{person_id}")
def get_person_route(person_id: str):
    return {
        "success": True,
        "person": require_person(person_id),
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
