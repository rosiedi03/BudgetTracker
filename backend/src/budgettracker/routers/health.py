from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from budgettracker.db import SessionDep

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(session: SessionDep, response: Response) -> dict[str, str]:
    """Returns 200 if the server and database are reachable, otherwise 503."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "database unavailable"}
    return {"status": "running"}
