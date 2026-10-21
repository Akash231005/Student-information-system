import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Student, UserAccount

router = APIRouter(prefix="/auth", tags=["authentication"])
bearer = HTTPBearer(auto_error=False)
_environment = settings.environment.lower()
TOKEN_SECRET = settings.token_secret
if not TOKEN_SECRET or (_environment in {"production", "prod"} and TOKEN_SECRET.startswith("replace-with")):
    if _environment in {"production", "prod"}:
        raise RuntimeError("SIS_TOKEN_SECRET must be set in production")
    TOKEN_SECRET = "development-only-change-this-secret-before-deployment"


class RegisterRequest(BaseModel):
    student_number: str = Field(min_length=1, max_length=32)
    full_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=10, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return base64.urlsafe_b64encode(salt + digest).decode()


def check_password(password: str, stored: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(stored.encode())
        salt, expected = raw[:16], raw[16:]
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def issue_token(account: UserAccount) -> str:
    payload = {"sub": account.id, "role": account.role, "exp": int(time.time()) + 3600}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).rstrip(b"=")
    signature = hmac.new(TOKEN_SECRET.encode(), encoded, hashlib.sha256).digest()
    signed = base64.urlsafe_b64encode(signature).rstrip(b"=")
    return encoded.decode() + "." + signed.decode()


def decode_token(token: str) -> dict:
    try:
        payload_part, signature_part = token.split(".", 1)
        expected = hmac.new(TOKEN_SECRET.encode(), payload_part.encode(), hashlib.sha256).digest()
        signature = base64.urlsafe_b64decode(signature_part + "=" * (-len(signature_part) % 4))
        if not hmac.compare_digest(expected, signature):
            raise ValueError("bad signature")
        payload = json.loads(base64.urlsafe_b64decode(
            payload_part + "=" * (-len(payload_part) % 4)
        ))
        if not isinstance(payload.get("sub"), int) or payload.get("role") not in {"STUDENT", "STAFF", "ADMIN"}:
            raise ValueError("invalid token claims")
        if payload["exp"] <= int(time.time()):
            raise ValueError("expired")
        return payload
    except (ValueError, KeyError, json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired bearer token") from exc


def current_account(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> UserAccount:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Bearer token required")
    payload = decode_token(credentials.credentials)
    account = db.get(UserAccount, payload["sub"])
    if account is None or account.role != payload["role"]:
        raise HTTPException(status_code=401, detail="Account is no longer valid")
    return account


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    student = Student(
        student_number=payload.student_number,
        full_name=payload.full_name,
        email=payload.email.lower().strip(),
    )
    db.add(student)
    try:
        db.flush()
        account = UserAccount(
            student_id=student.id,
            password_hash=hash_password(payload.password),
            role="STUDENT",
        )
        db.add(account)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Student number or email already exists") from exc
    return {"student_id": student.id, "email": student.email, "message": "Account created"}


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    account = db.scalar(
        select(UserAccount).join(Student).where(Student.email == payload.email.lower().strip())
    )
    if account is None or not check_password(payload.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": issue_token(account), "token_type": "bearer", "expires_in": 3600}


@router.get("/me")
def me(account: UserAccount = Depends(current_account), db: Session = Depends(get_db)):
    student = db.get(Student, account.student_id)
    return {"account_id": account.id, "role": account.role,
            "student_id": student.id, "student_number": student.student_number,
            "full_name": student.full_name, "email": student.email}

def require_staff(account: UserAccount = Depends(current_account)) -> UserAccount:
    if account.role not in {"STAFF", "ADMIN"}:
        raise HTTPException(status_code=403, detail="Staff role required")
    return account


def ensure_student_access(student_id: int, account: UserAccount) -> None:
    if account.role not in {"STAFF", "ADMIN"} and account.student_id != student_id:
        raise HTTPException(status_code=403, detail="Cannot access another student's records")
