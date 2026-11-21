"""One-time import from a read-only Django SQLite DB into an empty FastAPI DB."""
import argparse
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select

from backend.config import ROOT
from backend.database import SessionLocal
from backend.models import Document, User, UserDocument
from backend.services.storage import document_path


def parse_date(value):
    if not value:
        return None
    date = datetime.fromisoformat(value)
    return date.astimezone(timezone.utc).replace(tzinfo=None) if date.tzinfo else date


def migrate(source: Path, db):
    if any(db.scalar(select(func.count()).select_from(model)) for model in (User, Document, UserDocument)):
        raise ValueError("El destino debe estar vacío. No se sobrescribieron usuarios ni documentos.")
    if not source.is_file():
        raise ValueError("No se encontró la base de origen.")
    connection = sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        users = connection.execute("SELECT * FROM auth_user").fetchall()
        documents = connection.execute("SELECT * FROM documents_document").fetchall()
        entries = connection.execute("SELECT * FROM documents_userdocument").fetchall()
        for row in users:
            db.add(User(id=row["id"], username=row["username"], email=row["email"], password_hash=row["password"],
                        is_active=bool(row["is_active"]), is_admin=bool(row["is_superuser"]), created_at=parse_date(row["date_joined"])))
        db.flush()
        for row in documents:
            document = Document(id=str(uuid.UUID(row["id"])), storage_path=row["file"], original_name=row["original_name"],
                                extension=row["extension"], size=row["size"], extracted_text=row["extracted_text"], created_at=parse_date(row["created_at"]))
            if not document_path(document).is_file():
                raise ValueError("Falta un archivo original. Revisá MEDIA_ROOT antes de importar.")
            db.add(document)
        db.flush()
        for row in entries:
            interrupted = row["status"] == "processing"
            db.add(UserDocument(
                id=str(uuid.UUID(row["id"])), user_id=row["user_id"], document_id=str(uuid.UUID(row["document_id"])),
                sha256=row["sha256"], status="failed" if interrupted else row["status"],
                result=json.loads(row["result"]) if row["result"] else None,
                error_message="El procesamiento fue interrumpido por la migración. Podés reintentar." if interrupted else row["error_message"],
                model_name=row["model_name"], prompt_version=row["prompt_version"],
                attempt_id=str(uuid.UUID(row["attempt_id"])) if row["attempt_id"] else None,
                started_at=parse_date(row["started_at"]), completed_at=parse_date(row["completed_at"]), created_at=parse_date(row["created_at"]),
            ))
        db.commit()
        return {"users": len(users), "documents": len(documents), "user_documents": len(entries)}
    except Exception:
        db.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "db.sqlite3")
    args = parser.parse_args()
    with SessionLocal() as session:
        print(migrate(args.source, session))
