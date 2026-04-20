from __future__ import annotations

from fastapi.testclient import TestClient

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


def test_openapi_exposes_bearer_security_on_business_routes() -> None:
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()

    security_schemes = schema["components"]["securitySchemes"]
    assert "HTTPBearer" in security_schemes
    assert security_schemes["HTTPBearer"]["scheme"] == "bearer"

    protected_routes = [
        ("/markets", "get"),
        ("/debug/health", "get"),
        ("/market-stream/start/{asset_id}", "post"),
        ("/portfolios", "get"),
    ]

    for path, method in protected_routes:
        operation = schema["paths"][path][method]
        assert operation.get("security"), f"Expected security on {method.upper()} {path}"
