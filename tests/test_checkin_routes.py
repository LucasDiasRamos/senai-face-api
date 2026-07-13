from fastapi import FastAPI

from app.routes import checkin_routes


def create_test_app(fake_engine):
    app = FastAPI()
    app.state.face_engine = fake_engine
    app.include_router(checkin_routes.router, prefix="/api")
    return app


def test_checkin_face_accepts_image_without_person_id():
    app = create_test_app(fake_engine=object())
    schema = app.openapi()
    request_schema = schema["paths"]["/api/checkin-face"]["post"]["requestBody"]["content"]["multipart/form-data"]["schema"]
    ref_name = request_schema["$ref"].rsplit("/", 1)[-1]
    body_schema = schema["components"]["schemas"][ref_name]

    assert set(body_schema["properties"]) == {"image", "source", "robot_id"}
    assert body_schema["required"] == ["image"]
