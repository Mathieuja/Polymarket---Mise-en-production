from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("jose")
pytest.importorskip("passlib")
pytest.importorskip("boto3")
pytest.importorskip("redis")

from app.backend.api.main import app

pytestmark = [pytest.mark.unit, pytest.mark.component]


def test_login_success(monkeypatch) -> None:
    monkeypatch.setenv("BACKEND_MODE", "mock")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("DEMO_EMAIL", "demo@example.com")
    monkeypatch.setenv("DEMO_PASSWORD", "pw")

    with TestClient(app) as client:
        r = client.post("/auth/login", json={"email": "demo@example.com", "password": "pw"})

    assert r.status_code == 200
    data = r.json()
    assert data["token_type"] == "bearer"
    assert data["email"] == "demo@example.com"
    assert isinstance(data["access_token"], str)
    assert data["access_token"]


def test_login_invalid_credentials(monkeypatch) -> None:
    monkeypatch.setenv("BACKEND_MODE", "mock")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("DEMO_EMAIL", "demo@example.com")
    monkeypatch.setenv("DEMO_PASSWORD", "pw")

    with TestClient(app) as client:
        r = client.post("/auth/login", json={"email": "demo@example.com", "password": "wrong"})

    assert r.status_code == 401
