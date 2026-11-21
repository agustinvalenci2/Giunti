import json
import re
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .messages import LEGACY_PROCESSING_ERRORS
from .models import AuthSession, UserDocument, utcnow
from .security import current_session, mutation_session
from .services.files import ValidationError, validate_upload
from .services.pipeline import process_document, save_upload
from .services.storage import document_path

router = APIRouter(prefix="/api/documents", tags=["Documents"])


def owned_input(db, identifier, user_id):
    entry = db.scalar(select(UserDocument).where(UserDocument.id == str(identifier), UserDocument.user_id == user_id))
    if not entry:
        raise HTTPException(404, "Document not found.")
    return entry


def timestamp(value):
    return value.isoformat() + "Z" if value else None


def document_payload(entry, include_result=False):
    payload = {
        "id": entry.id, "original_name": entry.document.original_name, "extension": entry.document.extension,
        "size": entry.document.size, "status": entry.status, "created_at": timestamp(entry.created_at),
        "completed_at": timestamp(entry.completed_at),
        "error_message": LEGACY_PROCESSING_ERRORS.get(entry.error_message, entry.error_message),
        "total_items": entry.result.get("total_items") if entry.result else None,
        "can_process": entry.status in ("uploaded", "failed") or bool(entry.status == "processing" and entry.started_at and entry.started_at < utcnow() - timedelta(minutes=5)),
    }
    if include_result:
        payload["result"] = entry.result
    return payload


@router.get("")
def list_documents(page: int = Query(1, ge=1), session: AuthSession = Depends(current_session), db: Session = Depends(get_db)):
    scope = UserDocument.user_id == session.user_id
    total = db.scalar(select(func.count()).select_from(UserDocument).where(scope))
    completed = db.scalar(select(func.count()).select_from(UserDocument).where(scope, UserDocument.status == "completed"))
    entries = db.scalars(select(UserDocument).where(scope).order_by(UserDocument.created_at.desc()).offset((page - 1) * 12).limit(12)).all()
    return {"items": [document_payload(entry) for entry in entries], "page": page, "pages": max(1, (total + 11) // 12),
            "stats": {"total": total, "completed": completed, "pending": total - completed}}


@router.post("", status_code=201)
def upload_document(file: UploadFile = File(...), public_content: bool = Form(...),
                    session: AuthSession = Depends(mutation_session), db: Session = Depends(get_db)):
    try:
        if not public_content:
            raise HTTPException(422, "Confirm that the material is fictional or in the public domain and contains no personal information.")
        filename = re.sub(r"[\x00-\x1f\x7f]", "", (file.filename or "").replace("\\", "/").split("/")[-1])[:255]
        data = file.file.read(settings.MAX_UPLOAD_BYTES + 1)
        validated = validate_upload(filename, data)
        entry, created = save_upload(db, session.user_id, filename, data, validated)
        return {"document": document_payload(entry, True), "created": created}
    except ValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        file.file.close()


@router.get("/{identifier}")
def detail(identifier: UUID, session: AuthSession = Depends(current_session), db: Session = Depends(get_db)):
    return document_payload(owned_input(db, identifier, session.user_id), True)


@router.post("/{identifier}/process")
def process(identifier: UUID, session: AuthSession = Depends(mutation_session), db: Session = Depends(get_db)):
    entry = owned_input(db, identifier, session.user_id)
    process_document(db, entry)
    return document_payload(entry, True)


@router.get("/{identifier}/result")
def download_json(identifier: UUID, session: AuthSession = Depends(current_session), db: Session = Depends(get_db)):
    entry = owned_input(db, identifier, session.user_id)
    if entry.status != "completed" or entry.result is None:
        raise HTTPException(404, "The results are not available yet.")
    return Response(json.dumps(entry.result, ensure_ascii=False, indent=2), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="questionnaire-{entry.id}.json"', "Cache-Control": "private, no-store"})


@router.get("/{identifier}/original")
def download_original(identifier: UUID, session: AuthSession = Depends(current_session), db: Session = Depends(get_db)):
    entry = owned_input(db, identifier, session.user_id)
    path = document_path(entry.document)
    if not path.is_file():
        raise HTTPException(404, "Original file not found.")
    return FileResponse(path, filename=entry.document.original_name, media_type="application/octet-stream",
                        headers={"Cache-Control": "private, no-store"})
