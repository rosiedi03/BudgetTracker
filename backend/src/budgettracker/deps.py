"""Shared endpoint dependencies."""

import hashlib
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from budgettracker.db import DEV_USER_EMAIL, SessionDep
from budgettracker.models import AuthToken, User


# Temporary development user
def get_current_user(request: Request, session: SessionDep) -> User:
    user = session.scalar(select(User).where(User.email == DEV_USER_EMAIL))
    if user is None:
        raise RuntimeError("Dev user is missing")
    request.state.user_id = user.id
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]

bearer = HTTPBearer(auto_error=False)


# Verify authentication token
def get_authenticated_user(
    request: Request,
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    token = session.scalar(
        select(AuthToken).where(AuthToken.token_hash == token_hash)
    )

    if token is None or token.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = session.get(User, token.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    request.state.user_id = user.id
    return user


AuthenticatedUserDep = Annotated[User, Depends(get_authenticated_user)]
