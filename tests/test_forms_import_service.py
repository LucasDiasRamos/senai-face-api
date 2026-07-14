import zipfile

import numpy as np

from app.services import forms_import_service


class FakeFaceEngine:
    def __init__(self, error=None):
        self.error = error

    def get_embedding(self, image_bytes):
        if self.error:
            raise self.error
        return np.array([1.0, 0.0], dtype=np.float32)


def make_zip(path, files):
    with zipfile.ZipFile(path, "w") as archive:
        for filename, content in files.items():
            archive.writestr(filename, content)


def configure_common(monkeypatch, tmp_path, rows, existing_person=None):
    calls = []
    monkeypatch.setattr(forms_import_service, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(forms_import_service, "_load_rows", lambda excel_path: ({}, rows))
    monkeypatch.setattr(forms_import_service, "list_units", lambda: [{"id": 10, "name": "FATEC SENAI Campo Grande"}])
    monkeypatch.setattr(forms_import_service, "get_person", lambda person_id: existing_person)
    monkeypatch.setattr(forms_import_service, "register_log", lambda *args, **kwargs: calls.append(args))

    def fake_create_person_with_embedding(**kwargs):
        calls.append(("create", kwargs))

    monkeypatch.setattr(forms_import_service, "create_person_with_embedding", fake_create_person_with_embedding)
    return calls


def valid_row():
    return (2, {
        "forms_id": "1",
        "name": "Daniel Bastos",
        "unit": "FATEC SENAI CAMPO GRANDE",
        "role": "Aluno",
        "photo": "https://empresa.sharepoint.com/Fotos/Daniel%20Bastos_anonymous.jpeg",
        "consent": "Sim",
    })


def test_imports_new_person(monkeypatch, tmp_path):
    zip_path = tmp_path / "photos.zip"
    make_zip(zip_path, {"Fotos/Daniel Bastos_anonymous.jpeg": b"image"})
    calls = configure_common(monkeypatch, tmp_path, [valid_row()])

    report = forms_import_service.import_forms_people(tmp_path / "forms.xlsx", zip_path, FakeFaceEngine())

    assert report["imported"] == 1
    assert report["errors_count"] == 0
    create_call = [call for call in calls if call[0] == "create"][0]
    assert create_call[1]["person_id"] == "JP2026-0001"
    assert create_call[1]["unit_id"] == 10
    assert (tmp_path / "JP2026-0001-daniel-bastos.jpeg").exists()


def test_reimport_existing_person_with_photo_is_ignored(monkeypatch, tmp_path):
    zip_path = tmp_path / "photos.zip"
    make_zip(zip_path, {"Fotos/Daniel Bastos_anonymous.jpeg": b"image"})
    configure_common(
        monkeypatch,
        tmp_path,
        [valid_row()],
        existing_person={"person_id": "JP2026-0001", "name": "Daniel Bastos", "photos_count": 1},
    )

    report = forms_import_service.import_forms_people(tmp_path / "forms.xlsx", zip_path, FakeFaceEngine())

    assert report["ignored"] == 1
    assert report["imported"] == 0
    assert report["errors_count"] == 0


def test_missing_photo_does_not_create_person(monkeypatch, tmp_path):
    zip_path = tmp_path / "photos.zip"
    make_zip(zip_path, {"Fotos/Outra.jpeg": b"image"})
    calls = configure_common(monkeypatch, tmp_path, [valid_row()])

    report = forms_import_service.import_forms_people(tmp_path / "forms.xlsx", zip_path, FakeFaceEngine())

    assert report["errors_count"] == 1
    assert report["errors"][0]["code"] == "PHOTO_NOT_FOUND"
    assert not [call for call in calls if call[0] == "create"]


def test_existing_person_name_conflict(monkeypatch, tmp_path):
    zip_path = tmp_path / "photos.zip"
    make_zip(zip_path, {"Fotos/Daniel Bastos_anonymous.jpeg": b"image"})
    configure_common(
        monkeypatch,
        tmp_path,
        [valid_row()],
        existing_person={"person_id": "JP2026-0001", "name": "Maria Oliveira", "photos_count": 0},
    )

    report = forms_import_service.import_forms_people(tmp_path / "forms.xlsx", zip_path, FakeFaceEngine())

    assert report["errors_count"] == 1
    assert report["errors"][0]["code"] == "PERSON_DATA_CONFLICT"
