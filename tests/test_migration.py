import base64
import hashlib
import json
import sqlite3
import uuid

import pytest
from sqlalchemy import func, select

from backend.models import Document, User, UserDocument
from backend.security import verify_password
from scripts.migrate_django import migrate


def legacy_hash(password):
    salt, rounds = "fixture-salt", 10_000
    digest = base64.b64encode(hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), rounds)).decode()
    return f"pbkdf2_sha256${rounds}${salt}${digest}"


@pytest.fixture
def legacy_db(tmp_path, settings, pdf_bytes, result_data):
    source = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(source)
    connection.executescript('''
        CREATE TABLE auth_user(id INTEGER PRIMARY KEY, username TEXT, email TEXT, password TEXT, is_active INTEGER, is_superuser INTEGER, date_joined TEXT);
        CREATE TABLE documents_document(id TEXT PRIMARY KEY, file TEXT, original_name TEXT, extension TEXT, size INTEGER, extracted_text TEXT, created_at TEXT);
        CREATE TABLE documents_userdocument(id TEXT PRIMARY KEY, user_id INTEGER, document_id TEXT, sha256 TEXT, status TEXT, result TEXT, error_message TEXT, model_name TEXT, prompt_version TEXT, attempt_id TEXT, started_at TEXT, completed_at TEXT, created_at TEXT);
    ''')
    document_id, input_id = uuid.uuid4().hex, uuid.uuid4().hex
    connection.execute("INSERT INTO auth_user VALUES (1,?,?,?,?,?,?)", ("migrated", "m@example.com", legacy_hash("Preserved-password-427!"), 1, 0, "2026-01-01 12:00:00"))
    connection.execute("INSERT INTO documents_document VALUES (?,?,?,?,?,?,?)", (document_id, "legacy.pdf", "original.pdf", ".pdf", len(pdf_bytes), "", "2026-01-01 12:00:00"))
    connection.execute("INSERT INTO documents_userdocument VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (input_id, 1, document_id, hashlib.sha256(pdf_bytes).hexdigest(), "completed", json.dumps(result_data), "", "gemini-model", "v1", None, None, "2026-01-01 12:01:00", "2026-01-01 12:00:00"))
    connection.commit(); connection.close()
    settings.media_root.mkdir()
    (settings.media_root / "legacy.pdf").write_bytes(pdf_bytes)
    return source


def test_legacy_import_preserves_data_and_password_then_upgrades_on_login(db, legacy_db, client, result_data):
    original = legacy_db.read_bytes()
    counts = migrate(legacy_db, db)
    assert counts == {"users": 1, "documents": 1, "user_documents": 1}
    assert legacy_db.read_bytes() == original
    entry = db.scalar(select(UserDocument))
    assert entry.result == result_data and entry.document.original_name == "original.pdf"
    response = client.post("/api/auth/login", json={"username": "migrated", "password": "Preserved-password-427!"})
    assert response.status_code == 200
    db.expire_all()
    assert db.get(User, 1).password_hash.startswith("$argon2")
    assert client.get(f"/api/documents/{entry.id}/result").json() == result_data


def test_legacy_import_rolls_back_if_a_file_is_missing(db, legacy_db, settings):
    (settings.media_root / "legacy.pdf").unlink()
    with pytest.raises(ValueError, match="Falta un archivo"):
        migrate(legacy_db, db)
    assert db.scalar(select(func.count()).select_from(User)) == 0
    assert db.scalar(select(func.count()).select_from(Document)) == 0


def test_legacy_import_never_overwrites_nonempty_destination(db, legacy_db, user):
    with pytest.raises(ValueError, match="vacío"):
        migrate(legacy_db, db)
    assert db.scalar(select(func.count()).select_from(User)) == 1
    assert db.get(User, user.id).username == "ana"


def test_legacy_password_verification_rejects_wrong_password():
    encoded = legacy_hash("Keep-password-97!")
    assert verify_password("Keep-password-97!", encoded)
    assert not verify_password("incorrect", encoded)
