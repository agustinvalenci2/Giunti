import json
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen.canvas import Canvas
from sqlalchemy.orm import sessionmaker

from backend.config import settings as app_settings
from backend.database import Base, get_db, make_engine
from backend.main import create_app
from backend.models import User
from backend.security import hash_password


@pytest.fixture(autouse=True)
def settings(monkeypatch, tmp_path):
    monkeypatch.setattr(app_settings, "media_root", tmp_path / "media")
    monkeypatch.setattr(app_settings, "GEMINI_API_KEY", "test-key-never-sent")
    monkeypatch.setattr(app_settings, "debug", True)
    return app_settings


@pytest.fixture
def db_factory(tmp_path):
    engine = make_engine(f"sqlite:///{(tmp_path / 'test.sqlite3').as_posix()}")
    Base.metadata.create_all(engine)
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def db(db_factory):
    with db_factory() as session:
        yield session


@pytest.fixture
def client(db_factory):
    app = create_app()
    def override_db():
        with db_factory() as session:
            yield session
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client


@pytest.fixture
def user(db):
    user = User(username="ana", email="ana@example.com", password_hash=hash_password("Cuaderno-test-734!"))
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def authenticated(client, user):
    response = client.post("/api/auth/login", json={"username": "ana", "password": "Cuaderno-test-734!"})
    assert response.status_code == 200
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return client


@pytest.fixture
def pdf_bytes():
    stream = BytesIO()
    canvas = Canvas(stream)
    canvas.drawString(50, 780, "Cuestionario inventado")
    canvas.drawString(50, 750, "1. Describa una actividad que disfruta.")
    canvas.save()
    return stream.getvalue()


@pytest.fixture
def entry(db, user, pdf_bytes):
    from backend.services.files import validate_upload
    from backend.services.pipeline import save_upload
    return save_upload(db, user.id, "cuestionario.pdf", pdf_bytes, validate_upload("cuestionario.pdf", pdf_bytes))[0]


@pytest.fixture
def result_data():
    return json.loads((Path(__file__).resolve().parents[1] / "examples" / "cuestionario_inventado.json").read_text(encoding="utf-8"))


@pytest.fixture
def gemini_mock(monkeypatch, result_data):
    client = MagicMock()
    client.__enter__.return_value = client
    client.models.generate_content.return_value.text = json.dumps(result_data)
    constructor = MagicMock(return_value=client)
    monkeypatch.setattr("backend.services.gemini.genai.Client", constructor)
    return constructor, client
