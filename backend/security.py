import base64
import hashlib
import hmac
import secrets
from datetime import timedelta

from fastapi import Depends, HTTPException, Request, Response
from pwdlib import PasswordHash
from sqlalchemy import delete
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import AuthSession, User, utcnow

COOKIE_NAME = "cuaderno_session"
password_hasher = PasswordHash.recommended()
DUMMY_HASH = password_hasher.hash(secrets.token_urlsafe(24))


def hash_password(password):
    return password_hasher.hash(password)


def verify_password(password, encoded):
    # Keep existing Django accounts usable without importing Django at runtime.
    if encoded.startswith("pbkdf2_sha256$"):
        try:
            _, rounds, salt, expected = encoded.split("$", 3)
            iterations = int(rounds)
            if not 1 <= iterations <= 10_000_000:
                return False
            actual = base64.b64encode(hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)).decode()
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            return False
    try:
        return password_hasher.verify(password, encoded)
    except (ValueError, TypeError):
        return False


def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user: User, response: Response, old_token=None):
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= utcnow()))
    if old_token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == token_digest(old_token)))
    token = secrets.token_urlsafe(32)
    session = AuthSession(
        token_hash=token_digest(token), user_id=user.id,
        csrf_token=secrets.token_urlsafe(32), expires_at=utcnow() + timedelta(days=settings.session_days),
    )
    db.add(session)
    db.commit()
    response.set_cookie(COOKIE_NAME, token, httponly=True, secure=not settings.debug,
                        samesite="lax", max_age=settings.session_days * 86400, path="/")
    return session


def current_session(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME, "")
    session = db.get(AuthSession, token_digest(token)) if token else None
    if session is None or session.expires_at <= utcnow() or not session.user.is_active:
        raise HTTPException(401, "Ingresá a tu cuenta para continuar.")
    return session


def mutation_session(request: Request, session: AuthSession = Depends(current_session)):
    if not hmac.compare_digest(request.headers.get("X-CSRF-Token", ""), session.csrf_token):
        raise HTTPException(403, "La sesión de seguridad cambió. Actualizá la página e intentá nuevamente.")
    return session
