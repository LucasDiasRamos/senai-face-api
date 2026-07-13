import asyncio

import pytest

from app.services import checkin_service


class FakeUpload:
    pass


def run_async(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def silence_logs(monkeypatch):
    monkeypatch.setattr(checkin_service, "register_log", lambda *args, **kwargs: None)


def test_no_face_does_not_record_checkin(monkeypatch):
    async def fake_recognize_image(image, face_engine):
        return {"status": "no_face", "recognized": False, "face_count": 0, "confidence": None, "message": "Nenhum rosto"}

    monkeypatch.setattr(checkin_service, "recognize_image", fake_recognize_image)
    monkeypatch.setattr(checkin_service, "_record_checkin", lambda *args, **kwargs: pytest.fail("_record_checkin should not be called"))

    result = run_async(checkin_service.facial_checkin(FakeUpload(), object()))

    assert result["status"] == "no_face"
    assert result["checked_in"] is False


def test_multiple_faces_does_not_record_checkin(monkeypatch):
    async def fake_recognize_image(image, face_engine):
        return {"status": "multiple_faces", "recognized": False, "face_count": 2, "confidence": None, "message": "Mais de um rosto"}

    monkeypatch.setattr(checkin_service, "recognize_image", fake_recognize_image)
    monkeypatch.setattr(checkin_service, "_record_checkin", lambda *args, **kwargs: pytest.fail("_record_checkin should not be called"))

    result = run_async(checkin_service.facial_checkin(FakeUpload(), object()))

    assert result["status"] == "multiple_faces"
    assert result["face_count"] == 2


def test_not_recognized_does_not_record_checkin(monkeypatch):
    async def fake_recognize_image(image, face_engine):
        return {"status": "not_recognized", "recognized": False, "face_count": 1, "confidence": 0.2}

    monkeypatch.setattr(checkin_service, "recognize_image", fake_recognize_image)
    monkeypatch.setattr(checkin_service, "_record_checkin", lambda *args, **kwargs: pytest.fail("_record_checkin should not be called"))

    result = run_async(checkin_service.facial_checkin(FakeUpload(), object()))

    assert result["status"] == "not_recognized"
    assert result["checked_in"] is False


def test_low_confidence_does_not_record_checkin(monkeypatch):
    async def fake_recognize_image(image, face_engine):
        return {
            "status": "low_confidence",
            "recognized": True,
            "needs_confirmation": True,
            "face_count": 1,
            "person_id": "123",
            "name": "Pessoa",
            "confidence": 0.6,
        }

    monkeypatch.setattr(checkin_service, "recognize_image", fake_recognize_image)
    monkeypatch.setattr(checkin_service, "_record_checkin", lambda *args, **kwargs: pytest.fail("_record_checkin should not be called"))

    result = run_async(checkin_service.facial_checkin(FakeUpload(), object()))

    assert result["status"] == "low_confidence"
    assert result["possible_person"] == "Pessoa"


def test_valid_recognition_uses_recognized_person_id(monkeypatch):
    calls = []

    async def fake_recognize_image(image, face_engine):
        return {
            "status": "recognized",
            "recognized": True,
            "face_count": 1,
            "person_id": "123",
            "confidence": 0.8,
        }

    def fake_require_person(person_id):
        calls.append(("require_person", person_id))
        return {"person_id": person_id, "name": "Pessoa", "unit_id": 10, "unit": "Unidade", "role": "Visitante"}

    def fake_record_checkin(person, method, confidence=None):
        calls.append(("record", person["person_id"], method, confidence))
        return {
            "checked_in": True,
            "already_checked_in": False,
            "person_id": person["person_id"],
            "name": person["name"],
            "unit_id": person["unit_id"],
            "unit": person["unit"],
            "confidence": confidence,
            "message": "Credenciamento realizado com sucesso",
        }

    monkeypatch.setattr(checkin_service, "recognize_image", fake_recognize_image)
    monkeypatch.setattr(checkin_service, "require_person", fake_require_person)
    monkeypatch.setattr(checkin_service, "_record_checkin", fake_record_checkin)

    result = run_async(checkin_service.facial_checkin(FakeUpload(), object(), source="senia_android", robot_id="senia-01"))

    assert result["status"] == "recognized"
    assert result["person_id"] == "123"
    assert calls == [
        ("require_person", "123"),
        ("record", "123", "face", 0.8),
    ]
