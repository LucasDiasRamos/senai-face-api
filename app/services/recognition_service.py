from fastapi import HTTPException, UploadFile

from app.config import FACE_HIGH_THRESHOLD, FACE_MEDIUM_THRESHOLD
from app.database import load_all_embeddings
from app.face_engine import InvalidImageError, MultipleFacesFoundError, NoFaceFoundError
from app.services.log_service import register_log


def _format_match(match, score):
    return {
        "person_id": match["person_id"],
        "name": match["name"],
        "unit_id": match.get("unit_id"),
        "unit": match.get("unit"),
        "role": match.get("role"),
        "confidence": round(score, 4),
    }


def find_best_match(current_embedding, face_engine):
    registered_faces = load_all_embeddings()
    if not registered_faces:
        return None, -1.0

    best_match = None
    best_score = -1.0
    for person in registered_faces:
        score = face_engine.compare(current_embedding, person["embedding"])
        if score > best_score:
            best_score = score
            best_match = person

    return best_match, best_score


async def recognize_image(image: UploadFile, face_engine):
    image_bytes = await image.read()
    try:
        current_embedding = face_engine.get_embedding(image_bytes)
    except NoFaceFoundError as error:
        register_log("NO_FACE", None, str(error))
        return {
            "status": "no_face",
            "recognized": False,
            "face_count": 0,
            "confidence": None,
            "message": "Nenhum rosto encontrado. Olhe para a câmera e tente novamente.",
        }
    except MultipleFacesFoundError as error:
        register_log("MULTIPLE_FACES", None, str(error))
        return {
            "status": "multiple_faces",
            "recognized": False,
            "face_count": error.face_count,
            "confidence": None,
            "message": "Aproxime-se uma pessoa por vez para realizar o credenciamento.",
        }
    except InvalidImageError as error:
        register_log("RECOGNITION_ERROR", None, str(error))
        raise HTTPException(status_code=400, detail=str(error))
    except ValueError as error:
        register_log("RECOGNITION_ERROR", None, str(error))
        raise HTTPException(status_code=400, detail=str(error))

    best_match, best_score = find_best_match(current_embedding, face_engine)
    if not best_match:
        return {
            "status": "not_recognized",
            "recognized": False,
            "face_count": 1,
            "confidence": 0,
            "message": "Nenhuma face cadastrada",
        }

    match_data = _format_match(best_match, best_score)
    if best_score >= FACE_HIGH_THRESHOLD:
        return {
            "status": "recognized",
            "recognized": True,
            "needs_confirmation": False,
            "face_count": 1,
            **match_data,
            "message": "Pessoa reconhecida com alta confiança",
        }

    if best_score >= FACE_MEDIUM_THRESHOLD:
        register_log(
            "LOW_CONFIDENCE",
            best_match["person_id"],
            f"Reconhecimento com confiança insuficiente: {best_score:.4f}",
        )
        return {
            "status": "low_confidence",
            "recognized": True,
            "needs_confirmation": True,
            "face_count": 1,
            **match_data,
            "message": "Pessoa possivelmente reconhecida. Solicitar confirmação.",
        }

    register_log("LOW_CONFIDENCE", best_match["person_id"], "Pessoa não reconhecida")
    return {
        "status": "not_recognized",
        "recognized": False,
        "face_count": 1,
        "confidence": round(best_score, 4),
        "message": "Pessoa não reconhecida",
    }
