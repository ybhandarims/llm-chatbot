import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import main


def test_health_endpoint(monkeypatch):
    monkeypatch.setattr(main.redis_client, "ping", lambda: True)
    client = TestClient(main.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "auth"}
