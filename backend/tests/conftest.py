import os

# Keep tests hermetic: no background scheduler, no network probe.
os.environ.setdefault("ENABLE_SCHEDULER", "false")
os.environ.setdefault("PRICE_PROVIDER", "synthetic")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.base import SessionLocal, init_db
from app.db.models import User


@pytest.fixture(scope="session", autouse=True)
def seeded_db():
    init_db()
    with SessionLocal() as db:
        if not db.scalar(select(func.count(User.id))):
            from seed.seed_data import seed

            seed()
    yield


@pytest.fixture()
def client(seeded_db):
    from app.main import app

    with TestClient(app) as c:
        yield c


def _token(client, username: str, password: str) -> str:
    resp = client.post(
        "/api/auth/login", data={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture()
def admin_headers(client):
    return {"Authorization": f"Bearer {_token(client, 'admin', 'admin123')}"}


@pytest.fixture()
def manager1_headers(client):
    return {"Authorization": f"Bearer {_token(client, 'manager1', 'manager123')}"}
