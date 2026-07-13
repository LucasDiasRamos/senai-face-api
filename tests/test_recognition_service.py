import asyncio

import numpy as np
import pytest
from fastapi import HTTPException

from app.face_engine import InvalidImageError, MultipleFacesFoundError, NoFaceFoundError
from app.services import recognition_service


class FakeUpload:
    async def read(self):
        return b"image"


class FakeFaceEngine:
    def __init__(self, embedding=None, error=None, score=0.0):
        self.embedding = embedding if embedding is not None else np.array([1.0, 0.0], dtype=np.float32)
        self.error = error
        self.score = score

    def get_embedding(self, image_bytes):
        if self.error:
            raise self.error
        return self.embedding

    def compare(self, embedding_a, embedding_b):
        return self.score


def run_async(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def silence_logs(monkeypatch):
    monkeypatch.setattr(recognition_service, "register_log", lambda *args, **kwargs: None)


def test_invalid_image_raises_http_400():
    with pytest.raises(HTTPException) as exc:
        run_async(recognition_service.recognize_image(FakeUpload(), FakeFaceEngine(error=InvalidImageError("Imagem inválida"))))

    assert exc.value.status_code == 400


def test_no_face_returns_domain_result():
    result = run_async(recognition_service.recognize_image(FakeUpload(), FakeFaceEngine(error=NoFaceFoundError("Nenhum rosto encontrado"))))

    assert result["status"] == "no_face"
    assert result["face_count"] == 0
    assert result["recognized"] is False


def test_multiple_faces_returns_domain_result():
    result = run_async(recognition_service.recognize_image(FakeUpload(), FakeFaceEngine(error=MultipleFacesFoundError(2))))

    assert result["status"] == "multiple_faces"
    assert result["face_count"] == 2
    assert result["recognized"] is False


def test_no_registered_faces(monkeypatch):
    monkeypatch.setattr(recognition_service, "load_all_embeddings", lambda: [])

    result = run_async(recognition_service.recognize_image(FakeUpload(), FakeFaceEngine()))

    assert result["status"] == "not_recognized"
    assert result["face_count"] == 1
    assert result["confidence"] == 0


def test_score_below_medium_threshold(monkeypatch):
    monkeypatch.setattr(recognition_service, "load_all_embeddings", lambda: [{
        "person_id": "1",
        "name": "Pessoa",
        "unit_id": 10,
        "unit": "Unidade",
        "role": "Visitante",
        "embedding": np.array([1.0, 0.0], dtype=np.float32),
    }])

    result = run_async(recognition_service.recognize_image(FakeUpload(), FakeFaceEngine(score=0.1)))

    assert result["status"] == "not_recognized"
    assert result["recognized"] is False
    assert result["face_count"] == 1


def test_score_between_medium_and_high_threshold(monkeypatch):
    monkeypatch.setattr(recognition_service, "load_all_embeddings", lambda: [{
        "person_id": "1",
        "name": "Pessoa",
        "unit_id": 10,
        "unit": "Unidade",
        "role": "Visitante",
        "embedding": np.array([1.0, 0.0], dtype=np.float32),
    }])

    result = run_async(recognition_service.recognize_image(FakeUpload(), FakeFaceEngine(score=0.6)))

    assert result["status"] == "low_confidence"
    assert result["recognized"] is True
    assert result["needs_confirmation"] is True
    assert result["face_count"] == 1


def test_score_above_high_threshold(monkeypatch):
    monkeypatch.setattr(recognition_service, "load_all_embeddings", lambda: [{
        "person_id": "1",
        "name": "Pessoa",
        "unit_id": 10,
        "unit": "Unidade",
        "role": "Visitante",
        "embedding": np.array([1.0, 0.0], dtype=np.float32),
    }])

    result = run_async(recognition_service.recognize_image(FakeUpload(), FakeFaceEngine(score=0.8)))

    assert result["status"] == "recognized"
    assert result["recognized"] is True
    assert result["needs_confirmation"] is False
    assert result["face_count"] == 1
