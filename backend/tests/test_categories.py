"""GET /categories."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from budgettracker.models import Category


def test_lists_seeded_categories_in_id_order(client: TestClient):
    response = client.get("/categories")
    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "name": "Food"},
        {"id": 2, "name": "Transportation"},
        {"id": 3, "name": "Bills"},
        {"id": 4, "name": "Entertainment"},
        {"id": 5, "name": "Shopping"},
        {"id": 6, "name": "Other"},
    ]


def test_lists_categories_from_the_database(client: TestClient, session: Session):
    # A name that sorts first alphabetically still comes last, because it has the highest id.
    session.add(Category(name="Aardvark care"))
    session.commit()

    response = client.get("/categories")
    assert response.status_code == 200
    names = [category["name"] for category in response.json()]
    assert names[-1] == "Aardvark care"
    assert len(names) == 7


@pytest.mark.usefixtures("logged_out")
def test_requires_a_logged_in_user(client: TestClient):
    assert client.get("/categories").status_code == 401
