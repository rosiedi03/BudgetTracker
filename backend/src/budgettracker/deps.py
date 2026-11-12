"""Shared endpoint dependencies."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select

from budgettracker.db import DEV_USER_EMAIL, SessionDep
from budgettracker.models import User


def get_current_user(request: Request, session: SessionDep) -> User:
    """Return the user making the request.

    Temporary: always returns the dev user. Once login exists, this will look up the user from
    the request's token instead; endpoints using CurrentUserDep won't need to change.
    """
    user = session.scalar(select(User).where(User.email == DEV_USER_EMAIL))
    if user is None:
        raise RuntimeError("Dev user is missing; init_db() should have created it at startup")
    # Read by the request-logging middleware.
    request.state.user_id = user.id
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
