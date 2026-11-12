"""App-level behavior: health check, current user, and request logging."""

import logging
from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from budgettracker.db import DEV_USER_EMAIL, create_db_engine, get_session
from budgettracker.deps import CurrentUserDep
from budgettracker.main import app, log_requests

REQUEST_LOGGER = "budgettracker.requests"


@pytest.fixture
def probe_client() -> TestClient:
    """A small app with the real logging middleware and test-only routes.

    Keeps test routes out of the real app while exercising the same middleware and dependencies.
    """
    probe = FastAPI()
    probe.middleware("http")(log_requests)

    @probe.get("/whoami")
    def whoami(user: CurrentUserDep) -> dict:
        return {"id": user.id, "email": user.email}

    @probe.post("/submit")
    def submit(_data: dict) -> dict:
        return {}

    @probe.get("/fail")
    def fail() -> None:
        raise RuntimeError("internal detail that must not reach the client")

    probe.dependency_overrides = app.dependency_overrides
    return TestClient(probe)


def request_log_lines(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == REQUEST_LOGGER]


# Health check


def test_health_returns_200_when_database_is_reachable(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "running"}


def test_health_returns_503_when_database_is_unreachable(client: TestClient, tmp_path):
    # A path inside a directory that doesn't exist, so SQLite can't open it.
    broken_engine = create_db_engine(f"sqlite:///{tmp_path / 'missing' / 'db.sqlite'}")

    def get_broken_session() -> Generator[Session]:
        with Session(broken_engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_broken_session
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "database unavailable"}


# Current user


def test_current_user_is_the_dev_user(probe_client: TestClient):
    response = probe_client.get("/whoami")
    assert response.status_code == 200
    assert response.json()["email"] == DEV_USER_EMAIL


# Request logging


def test_each_request_is_logged_by_the_real_app(client: TestClient, caplog):
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER)
    client.get("/health")
    lines = request_log_lines(caplog)
    assert len(lines) == 1
    assert lines[0].startswith("GET /health 200 ")
    assert lines[0].endswith(" user=None")


def test_request_log_includes_the_current_user_id(probe_client: TestClient, caplog):
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER)
    user_id = probe_client.get("/whoami").json()["id"]
    assert request_log_lines(caplog)[-1].endswith(f" user={user_id}")


def test_request_bodies_and_query_strings_are_not_logged(probe_client: TestClient, caplog):
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER)
    probe_client.post("/submit", json={"password": "body-secret-123"})
    probe_client.get("/whoami?token=query-secret-456")
    logged = "\n".join(request_log_lines(caplog))
    assert len(request_log_lines(caplog)) == 2
    assert "body-secret-123" not in logged
    assert "query-secret-456" not in logged


def test_unhandled_error_returns_generic_500_and_logs_traceback(probe_client: TestClient, caplog):
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER)
    response = probe_client.get("/fail")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}

    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(error_records) == 1
    assert error_records[0].exc_info is not None  # traceback attached
    assert request_log_lines(caplog)[-1].startswith("GET /fail 500 ")
