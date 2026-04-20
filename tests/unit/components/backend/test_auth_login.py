from __future__ import annotations

from uuid import uuid4

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


def test_login_sets_cookie_and_authorizes_followup_requests(monkeypatch) -> None:
    email = f"cookie-{uuid4().hex[:8]}@example.com"

    monkeypatch.setenv("BACKEND_MODE", "api")
    monkeypatch.setenv("JWT_SECRET", "test-secret")

    with TestClient(app) as client:
        register_response = client.post(
            "/auth/register",
            json={"name": "Cookie User", "email": email, "password": "password123"},
        )
        assert register_response.status_code == 201
        assert register_response.cookies.get("access_token")

        login_response = client.post(
            "/auth/login",
            json={"email": email, "password": "password123"},
        )

        assert login_response.status_code == 200
        assert login_response.cookies.get("access_token")

        me_response = client.get("/auth/me")

    assert me_response.status_code == 200
    assert me_response.json()["email"] == email
