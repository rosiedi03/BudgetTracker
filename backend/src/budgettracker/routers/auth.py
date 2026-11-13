import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException
from pwdlib import PasswordHash
from pydantic import BaseModel, Field
from sqlalchemy import select

from budgettracker.db import SessionDep
from budgettracker.deps import AuthenticatedUserDep
from budgettracker.models import AuthToken
from budgettracker.models import User as DBUser

router = APIRouter(tags=["auth"])
password_hash = PasswordHash.recommended()


class RegisterData(BaseModel):
    email: str
    password: str = Field(min_length=8)


class LoginData(BaseModel):
    email: str
    password: str


# Register and save the user in SQLite
@router.post("/register")
def register(data: RegisterData, session: SessionDep):
    email = data.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="Invalid email")
    existing = session.scalar(select(DBUser).where(DBUser.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    user = DBUser(email=email, password_hash=password_hash.hash(data.password))
    session.add(user)
    session.commit()
    return {"message": "Registration successful"}


# Verify credentials and generate a secure token
@router.post("/login")
def login(data: LoginData, session: SessionDep):
    email = data.email.strip().lower()
    user = session.scalar(select(DBUser).where(DBUser.email == email))
    if not user or not password_hash.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    session.add(
        AuthToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
    )
    session.commit()
    return {"message": "Login successful", "access_token": token, "token_type": "bearer"}


# Return the logged-in user's information
@router.get("/me")
def get_my_profile(user: AuthenticatedUserDep):
    return {"id": user.id, "email": user.email}
