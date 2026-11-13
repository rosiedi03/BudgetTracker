"""Shared endpoint dependencies."""

import hashlib
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from budgettracker.db import SessionDep
from budgettracker.models import AuthToken, User

bearer = HTTPBearer(auto_error=False)


def hash_token(token: str) -> str:
    """The value stored for a login token. Tokens themselves are never stored."""
    return hashlib.sha256(token.encode()).hexdigest()


# Verify authentication token
def get_authenticated_user(
    request: Request,
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    token_hash = hash_token(credentials.credentials)
    token = session.scalar(select(AuthToken).where(AuthToken.token_hash == token_hash))

    if token is None or token.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = session.get(User, token.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    request.state.user_id = user.id
    return user


AuthenticatedUserDep = Annotated[User, Depends(get_authenticated_user)]
