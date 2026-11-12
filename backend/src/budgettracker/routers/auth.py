"""PLACEHOLDER: in-memory register/login routes, to be replaced by database-backed ones."""

from fastapi import APIRouter, HTTPException
from pwdlib import PasswordHash
from pydantic import BaseModel, Field

router = APIRouter(tags=["auth"])

# Password hashing and temporary user storage
password_hash = PasswordHash.recommended()
users = {}


class User(BaseModel):
    email: str
    password: str = Field(min_length=8)


# Register a new user
@router.post("/register")
def register(user: User):
    email = user.email.strip().lower()
    if email in users:
        raise HTTPException(status_code=409, detail="User already exists")
    users[email] = password_hash.hash(user.password)
    return {"message": "Registration successful"}


# Verify user login
@router.post("/login")
def login(user: User):
    email = user.email.strip().lower()
    saved_password = users.get(email)
    if not saved_password or not password_hash.verify(user.password, saved_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful"}
