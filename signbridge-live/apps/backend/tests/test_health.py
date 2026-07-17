import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-ID" in response.headers


def test_api_v1_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_detailed_health_with_dependencies_disabled(client: TestClient) -> None:
    response = client.get("/api/v1/health/detailed")
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "healthy"
    assert len(payload["data"]["dependencies"]) == 1

    dependency_names = {item["name"] for item in payload["data"]["dependencies"]}
    assert dependency_names == {"supabase"}


def test_settings_load_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("APP_NAME", "SignBridge Test")
    monkeypatch.setenv("ENVIRONMENT", "staging")

    settings = Settings()
    assert settings.APP_NAME == "SignBridge Test"
    assert settings.ENVIRONMENT == "staging"

    get_settings.cache_clear()


def test_cors_origins_parsed_from_comma_separated_string() -> None:
    settings = Settings(CORS_ORIGINS="http://a.test, http://b.test")
    assert settings.CORS_ORIGINS == ["http://a.test", "http://b.test"]
