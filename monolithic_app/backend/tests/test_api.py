from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_prompt_and_chat_flow(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # Use mock mode to avoid external dependency in tests.
    monkeypatch.setenv("OPENAI_MOCK", "true")

    prompt_update = client.put(
        "/api/settings/system-prompt",
        json={"system_prompt": "You are a test assistant."},
    )
    assert prompt_update.status_code == 200

    send_response = client.post(
        "/api/chat/send",
        json={"message": "Hello from tests"},
    )
    assert send_response.status_code == 200
    payload = send_response.json()
    conversation_id = payload["conversation"]["id"]

    list_response = client.get("/api/conversations")
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 1

    detail_response = client.get(f"/api/conversations/{conversation_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["messages"]) >= 2
