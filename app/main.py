from pathlib import Path


from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.face_engine import FaceEngine
from app.routes import checkin_routes, health_routes, logs_routes, people_routes, recognition_routes, units_routes


STATIC_DIR = Path(__file__).resolve().parent / "static"


app = FastAPI(
    title="Senia Face API",
    description="API local de reconhecimento facial e credenciamento para a Senia",
    version="0.2.0",
)


@app.on_event("startup")
def startup():
    init_db()
    app.state.face_engine = FaceEngine()


@app.get("/")
def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/app")
def frontend_app():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/frontend")
def frontend():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/frontend/")
def frontend_slash():
    return FileResponse(STATIC_DIR / "index.html")


app.include_router(health_routes.router)
app.include_router(units_routes.router)
app.include_router(people_routes.router)
app.include_router(recognition_routes.router)
app.include_router(checkin_routes.router)
app.include_router(logs_routes.router)
app.include_router(health_routes.router, prefix="/api")
app.include_router(units_routes.router, prefix="/api")
app.include_router(people_routes.router, prefix="/api")
app.include_router(recognition_routes.router, prefix="/api")
app.include_router(checkin_routes.router, prefix="/api")
app.include_router(logs_routes.router, prefix="/api")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
