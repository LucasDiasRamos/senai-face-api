from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.database import save_person
from app.services.log_service import register_log
from app.services.recognition_service import recognize_image


router = APIRouter()


@router.post("/recognize")
async def recognize_route(request: Request, image: UploadFile = File(...)):
    return await recognize_image(image, request.app.state.face_engine)


@router.post("/enroll")
async def enroll_compat_route(
    request: Request,
    person_id: str = Form(...),
    name: str = Form(...),
    unit_id: int | None = Form(None),
    unit: str | None = Form(None),
    image: UploadFile = File(...),
):
    try:
        image_bytes = await image.read()
        embedding = request.app.state.face_engine.get_embedding(image_bytes)
        save_person(person_id, name, embedding, unit_id=unit_id, unit=unit)
        register_log("ENROLL", person_id, "Cadastro compatível via /enroll")
        return {
            "success": True,
            "person_id": person_id,
            "name": name,
            "unit_id": unit_id,
            "message": "Pessoa cadastrada com sucesso",
        }
    except ValueError as error:
        register_log("ENROLL_ERROR", person_id, str(error))
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        register_log("ENROLL_ERROR", person_id, str(error))
        raise HTTPException(status_code=400, detail=str(error))
