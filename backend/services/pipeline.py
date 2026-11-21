import logging
import uuid
from datetime import timedelta

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Document, UserDocument, utcnow
from backend.services.gemini import PROMPT_VERSION, ProcessingError, extract_questionnaire
from backend.services.storage import document_path

logger = logging.getLogger(__name__)


def save_upload(db: Session, user_id: int, filename: str, data: bytes, validated):
    query = select(UserDocument).where(UserDocument.user_id == user_id, UserDocument.sha256 == validated.sha256)
    existing = db.scalar(query)
    if existing:
        return existing, False
    identifier = str(uuid.uuid4())
    document = Document(
        id=identifier, original_name=filename, extension=validated.extension, size=validated.size,
        extracted_text=validated.text, storage_path=f"documents/{identifier}{validated.extension}",
    )
    path = document_path(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as output:
            output.write(data)
        db.add(document)
        db.flush()
        entry = UserDocument(user_id=user_id, document=document, sha256=validated.sha256)
        db.add(entry)
        db.commit()
        return entry, True
    except Exception as exc:
        db.rollback()
        path.unlink(missing_ok=True)
        if isinstance(exc, IntegrityError):
            existing = db.scalar(query)
            if existing:
                return existing, False
        raise


def process_document(db: Session, entry: UserDocument):
    now, attempt = utcnow(), str(uuid.uuid4())
    eligible = or_(UserDocument.status.in_(["uploaded", "failed"]), and_(
        UserDocument.status == "processing", UserDocument.started_at < now - timedelta(minutes=5),
    ))
    scope = [UserDocument.id == entry.id, UserDocument.user_id == entry.user_id]
    claimed = db.execute(update(UserDocument).where(*scope, eligible).values(
        status="processing", attempt_id=attempt, started_at=now, error_message="",
        model_name=settings.GEMINI_MODEL, prompt_version=PROMPT_VERSION,
    ).execution_options(synchronize_session=False)).rowcount
    db.commit()
    db.refresh(entry)
    if not claimed:
        return False
    # Release the read transaction before waiting for an external service.
    document = entry.document
    db.commit()
    try:
        result = extract_questionnaire(document)
    except Exception as exc:
        message = str(exc) if isinstance(exc, ProcessingError) else "Ocurrió un error al procesar el archivo. Podés reintentar."
        if not isinstance(exc, ProcessingError):
            logger.error("Processing failed for input %s (%s)", entry.id, type(exc).__name__)
        values = {"status": "failed", "error_message": message}
    else:
        values = {"status": "completed", "result": result, "error_message": "", "completed_at": utcnow()}
    db.execute(update(UserDocument).where(*scope, UserDocument.attempt_id == attempt).values(**values)
               .execution_options(synchronize_session=False))
    db.commit()
    db.refresh(entry)
    return True
