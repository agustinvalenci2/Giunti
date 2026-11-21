import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .config import settings
from .models import AuthSession, User
from .security import (COOKIE_NAME, DUMMY_HASH, create_session, current_session,
                       hash_password, mutation_session, verify_password)

router = APIRouter(prefix="/api/auth", tags=["Users"])


class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=256)


class RegisterInput(LoginInput):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=10, max_length=256)

    @field_validator("username")
    @classmethod
    def valid_username(cls, value):
        if not re.fullmatch(r"[\w.@+-]+", value):
            raise ValueError("Use letters, numbers, or these characters: @ . + - _.")
        return value

    @field_validator("password")
    @classmethod
    def valid_password(cls, value):
        if value.isdecimal() or value.lower() in {"password123", "contraseña123", "qwerty12345", "1234567890"}:
            raise ValueError("Choose a less predictable password.")
        return value


def user_payload(user):
    return {"id": user.id, "username": user.username, "email": user.email}


def session_payload(session, user=None):
    return {"user": user_payload(user or session.user), "csrf_token": session.csrf_token}


def require_json(request):
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        raise HTTPException(415, "This request requires JSON.")


@router.post("/register", status_code=201)
def register(data: RegisterInput, request: Request, response: Response, db: Session = Depends(get_db)):
    require_json(request)
    user = User(username=data.username, email=str(data.email), password_hash=hash_password(data.password))
    db.add(user)
    try:
        db.flush()
        session = create_session(db, user, response, request.cookies.get(COOKIE_NAME))
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "That username is already taken.")
    return session_payload(session, user)


@router.post("/login")
def login(data: LoginInput, request: Request, response: Response, db: Session = Depends(get_db)):
    require_json(request)
    user = db.scalar(select(User).where(User.username == data.username))
    valid = verify_password(data.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid or not user.is_active:
        raise HTTPException(401, "The username or password is incorrect.")
    if user.password_hash.startswith("pbkdf2_sha256$"):
        user.password_hash = hash_password(data.password)
    session = create_session(db, user, response, request.cookies.get(COOKIE_NAME))
    return session_payload(session, user)


@router.get("/me")
def me(session: AuthSession = Depends(current_session)):
    return session_payload(session)


@router.post("/logout", status_code=204)
def logout(response: Response, session: AuthSession = Depends(mutation_session), db: Session = Depends(get_db)):
    db.delete(session)
    db.commit()
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=not settings.debug, samesite="lax")
