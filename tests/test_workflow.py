from datetime import timedelta

import pytest
from google.genai.errors import ClientError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from backend.models import AuthSession, Document, User, UserDocument, utcnow
from backend.security import COOKIE_NAME, hash_password, token_digest
from backend.services.files import validate_upload
from backend.services.pipeline import process_document, save_upload
from backend.services.storage import document_path


def test_same_user_same_bytes_reuses_record_with_different_name(db, user, entry, pdf_bytes):
    saved, created = save_upload(db, user.id, "renamed.pdf", pdf_bytes, validate_upload("renamed.pdf", pdf_bytes))
    assert not created and saved.id == entry.id
    assert db.scalar(select(func.count()).select_from(Document)) == 1


def test_other_user_has_independent_record(db, entry, pdf_bytes):
    other = User(username="other", email="other@example.com", password_hash=hash_password("Something-unknown-52!"))
    db.add(other); db.commit()
    saved, created = save_upload(db, other.id, "test.pdf", pdf_bytes, validate_upload("test.pdf", pdf_bytes))
    assert created and saved.document_id != entry.document_id and saved.result is None


def test_database_enforces_hash_uniqueness(db, user, entry):
    document = Document(storage_path="unused.pdf", original_name="test.pdf", extension=".pdf", size=1)
    db.add(document); db.flush()
    db.add(UserDocument(user_id=user.id, document=document, sha256=entry.sha256))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_extraction_persists_and_is_not_called_twice(db, entry, gemini_mock, result_data):
    constructor, client = gemini_mock
    assert process_document(db, entry)
    assert entry.status == "completed" and entry.result == result_data
    assert not process_document(db, entry)
    assert client.models.generate_content.call_count == 1
    kwargs = client.models.generate_content.call_args.kwargs
    assert kwargs["contents"][0].inline_data.mime_type == "application/pdf"
    assert kwargs["config"].response_json_schema["properties"]["items"]
    assert constructor.call_args.kwargs["http_options"].retry_options.attempts == 1


def test_spreadsheet_text_sent_instead_of_binary(db, entry, gemini_mock):
    entry.document.extension = ".xls"
    entry.document.extracted_text = "1. Describa una actividad."
    db.commit()
    process_document(db, entry)
    part = gemini_mock[1].models.generate_content.call_args.kwargs["contents"][0]
    assert part.text == entry.document.extracted_text and part.inline_data is None


def test_missing_key_preserves_file_and_allows_retry(db, entry, settings, gemini_mock, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    process_document(db, entry)
    assert entry.status == "failed" and "GEMINI_API_KEY" in entry.error_message
    assert document_path(entry.document).is_file()
    gemini_mock[0].assert_not_called()
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-only")
    process_document(db, entry)
    assert entry.status == "completed"


@pytest.mark.parametrize("raw", ["not json", '{"titulo":"Vacío","idioma":"es","total_items":0,"items":[]}', '{"total_items":999}'])
def test_invalid_or_empty_results_not_cached(db, entry, gemini_mock, raw):
    gemini_mock[1].models.generate_content.return_value.text = raw
    process_document(db, entry)
    assert entry.status == "failed" and entry.result is None and entry.error_message


def test_quota_error_is_safe(db, entry, gemini_mock):
    gemini_mock[1].models.generate_content.side_effect = ClientError(429, {"error": {"message": "secret-sensitive-provider-body"}})
    process_document(db, entry)
    assert entry.status == "failed" and "cuota" in entry.error_message and "secret" not in entry.error_message


def test_live_attempt_cannot_be_duplicated_but_stale_attempt_can_retry(db, entry, gemini_mock):
    entry.status, entry.started_at = "processing", utcnow()
    db.commit()
    assert not process_document(db, entry)
    gemini_mock[0].assert_not_called()
    entry.started_at = utcnow() - timedelta(minutes=6)
    db.commit()
    assert process_document(db, entry) and entry.status == "completed"


@pytest.mark.parametrize("route", ["", "/process", "/original", "/result"])
def test_cross_user_access_denied(client, entry, route, gemini_mock):
    response = client.post("/api/auth/register", json={"username": "outsider", "email": "o@example.com", "password": "Other-password-781!"})
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    path = f"/api/documents/{entry.id}{route}"
    response = client.post(path) if route == "/process" else client.get(path)
    assert response.status_code == 404
    assert client.get("/api/documents").json()["stats"]["total"] == 0
    gemini_mock[0].assert_not_called()


def test_unauthenticated_access_denied(client, entry):
    assert client.get(f"/api/documents/{entry.id}").status_code == 401


def test_upload_process_download_end_to_end(authenticated, pdf_bytes, gemini_mock, result_data):
    client = authenticated
    response = client.post("/api/documents", files={"file": ("test.pdf", pdf_bytes, "application/pdf")}, data={"public_content": "true"})
    assert response.status_code == 201
    identifier = response.json()["document"]["id"]
    assert client.get(f"/api/documents/{identifier}").status_code == 200
    processed = client.post(f"/api/documents/{identifier}/process")
    assert processed.status_code == 200 and processed.json()["status"] == "completed"
    assert client.get(f"/api/documents/{identifier}/result").json() == result_data
    original = client.get(f"/api/documents/{identifier}/original")
    assert original.content == pdf_bytes and original.headers["cache-control"] == "private, no-store"
    duplicate = client.post("/api/documents", files={"file": ("renamed.pdf", pdf_bytes)}, data={"public_content": "true"})
    assert not duplicate.json()["created"] and duplicate.json()["document"]["result"] == result_data
    client.post(f"/api/documents/{identifier}/process")
    assert gemini_mock[1].models.generate_content.call_count == 1


def test_registration_login_logout_and_csrf(client):
    data = {"username": "newuser", "email": "demo@example.com", "password": "Example-pass-927!"}
    response = client.post("/api/auth/register", json=data)
    assert response.status_code == 201 and "HttpOnly" in response.headers["set-cookie"]
    assert client.get("/api/auth/me").json()["user"]["username"] == "newuser"
    assert client.post("/api/auth/logout").status_code == 403
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json={"username": data["username"], "password": data["password"]}).status_code == 200


def test_wrong_password_rejected(client, user):
    assert client.post("/api/auth/login", json={"username": "ana", "password": "wrong-pass"}).status_code == 401


def test_expired_session_rejected(authenticated, db):
    session = db.get(AuthSession, token_digest(authenticated.cookies.get(COOKIE_NAME)))
    session.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert authenticated.get("/api/auth/me").status_code == 401


def test_cross_origin_mutations_rejected(authenticated):
    assert authenticated.post("/api/auth/logout", headers={"Origin": "https://untrusted.example"}).status_code == 403


def test_upload_requires_csrf_and_consent(authenticated, pdf_bytes):
    response = authenticated.post("/api/documents", files={"file": ("test.pdf", pdf_bytes)}, data={"public_content": "false"})
    assert response.status_code == 422
    authenticated.headers.pop("X-CSRF-Token")
    assert authenticated.post("/api/documents", files={"file": ("test.pdf", pdf_bytes)}, data={"public_content": "true"}).status_code == 403


def test_password_is_not_reflected_in_validation_error(client):
    password = "short"
    response = client.post("/api/auth/register", json={"username": "x", "email": "bad", "password": password})
    assert response.status_code == 422 and password not in response.text and '"input"' not in response.text


def test_private_media_and_unknown_api_do_not_fall_back_to_spa(client, entry):
    assert client.get(f"/media/{entry.document.storage_path}").status_code == 404
    assert client.get("/api/missing").status_code == 404
    assert client.get("/api/health").json()["framework"] == "FastAPI"
