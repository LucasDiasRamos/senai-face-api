from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.face_engine import FaceEngine
from app.database import init_db, save_person, load_all_embeddings

STATIC_DIR = Path(__file__).resolve().parent / "static"


app = FastAPI(
    title="Senia Face API",
    description="API local de reconhecimento facial para a Senia",
    version="0.1.0"
)

face_engine = FaceEngine()


@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def root():
    return {
        "message": "Senia Face API online",
        "docs": "/docs",
        "frontend": "/frontend",
        "health": "/health"
    }


@app.get("/app")
def frontend_app():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/frontend")
def frontend():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/frontend/")
def frontend_slash():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/health")
def health():
    return {
        "status": "online",
        "service": "senia-face-api"
    }


@app.post("/enroll")
async def enroll(
    person_id: str = Form(...),
    name: str = Form(...),
    image: UploadFile = File(...)
):
    try:
        image_bytes = await image.read()
        embedding = face_engine.get_embedding(image_bytes)

        save_person(person_id, name, embedding)

        return {
            "success": True,
            "person_id": person_id,
            "name": name,
            "message": "Pessoa cadastrada com sucesso"
        }

    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.post("/recognize")
async def recognize(image: UploadFile = File(...)):
    try:
        image_bytes = await image.read()
        current_embedding = face_engine.get_embedding(image_bytes)

        registered_faces = load_all_embeddings()

        if not registered_faces:
            return {
                "recognized": False,
                "message": "Nenhuma face cadastrada"
            }

        best_match = None
        best_score = -1.0

        for person in registered_faces:
            score = face_engine.compare(
                current_embedding,
                person["embedding"]
            )

            if score > best_score:
                best_score = score
                best_match = person

        high_threshold = 0.65
        medium_threshold = 0.50

        if best_score >= high_threshold:
            return {
                "recognized": True,
                "needs_confirmation": False,
                "person_id": best_match["person_id"],
                "name": best_match["name"],
                "confidence": round(best_score, 4),
                "message": "Pessoa reconhecida com alta confiança"
            }

        if best_score >= medium_threshold:
            return {
                "recognized": True,
                "needs_confirmation": True,
                "person_id": best_match["person_id"],
                "name": best_match["name"],
                "confidence": round(best_score, 4),
                "message": "Pessoa possivelmente reconhecida. Solicitar confirmação."
            }

        return {
            "recognized": False,
            "confidence": round(best_score, 4),
            "message": "Pessoa não reconhecida"
        }

    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))
