from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "online",
        "service": "senia-face-api",
    }
