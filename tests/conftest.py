"""Fixtures de pruebas: cliente FastAPI con SQLite en memoria."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app


@pytest.fixture
def session():
    # SQLite en memoria compartida entre conexiones del mismo test.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(session):
    def _get_session_override():
        yield session

    app.dependency_overrides[get_session] = _get_session_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def dispositivo(client):
    """Crea un dispositivo de prueba y devuelve su id."""
    r = client.post("/api/dispositivos", json={"nombre": "Cocina Test"})
    assert r.status_code == 201
    return r.json()["id"]
