from fastapi import APIRouter
from sqlalchemy import select

from budgettracker.db import SessionDep
from budgettracker.deps import AuthenticatedUserDep
from budgettracker.models import Category
from budgettracker.schemas.categories import CategoryOut

router = APIRouter(tags=["categories"])


@router.get("/categories")
def list_categories(session: SessionDep, _user: AuthenticatedUserDep) -> list[CategoryOut]:
    """All expense categories, in id order. Categories are shared, but login is still required."""
    categories = session.scalars(select(Category).order_by(Category.id))
    return [CategoryOut(id=category.id, name=category.name) for category in categories]
