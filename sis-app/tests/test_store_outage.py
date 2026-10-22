"""A dropped store must answer 503 with the store named, never an unexplained 500."""
import redis
from fastapi.testclient import TestClient

from app import extended, main


def test_rate_limiter_outage_answers_503(monkeypatch):
    # conftest disables the limiter; this test is the one that wants it on.
    monkeypatch.setattr(main, "RATE_LIMIT_ENABLED", True)

    def refuse(key, now=None):
        raise redis.exceptions.ConnectionError("Error 111 connecting to 127.0.0.1:6379")

    monkeypatch.setattr(main.api_limiter, "allow", refuse)
    with TestClient(main.app) as client:
        response = client.get("/courses")

    assert response.status_code == 503
    assert response.json()["store"] == "redis"


def test_cache_outage_answers_503(monkeypatch):
    def refuse(*args, **kwargs):
        raise redis.exceptions.ConnectionError("Error 111 connecting to 127.0.0.1:6379")

    monkeypatch.setattr(extended.cache, "get", refuse)
    with TestClient(main.app) as client:
        response = client.get("/autocomplete", params={"q": "SD"})

    assert response.status_code == 503
    assert response.json()["store"] == "redis"
