from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("jose")
pytest.importorskip("passlib")
pytest.importorskip("boto3")
pytest.importorskip("redis")

from app.backend.api.main import app


def test_api_lifespan_starts_and_stops() -> None:
    with TestClient(app) as client:
        assert app.state.is_started is True
        openapi_response = client.get("/openapi.json")
        assert openapi_response.status_code == 200

    assert app.state.is_started is False


def test_health_endpoint_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_exposes_query_token_on_business_routes() -> None:
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()

    protected_routes = [
        ("/markets", "get"),
        ("/debug/health", "get"),
        ("/market-stream/start/{asset_id}", "post"),
        ("/portfolios", "get"),
    ]

    for path, method in protected_routes:
        operation = schema["paths"][path][method]
        token_params = [
            param
            for param in operation.get("parameters", [])
            if param.get("name") == "token" and param.get("in") == "query"
        ]
        assert token_params, f"Expected query token on {method.upper()} {path}"
