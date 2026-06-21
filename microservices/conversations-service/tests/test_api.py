import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DIR = Path(__file__).resolve().parent
SERVICE_MAIN = TEST_DIR.parent / "main.py"

spec = importlib.util.spec_from_file_location(
    "conversations_service_main", SERVICE_MAIN
)
if spec is None or spec.loader is None:
    raise ImportError(f"Unable to load service module from {SERVICE_MAIN}")

svc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(svc)


class FakeTable:
    def __init__(self):
        self.items = {}

    def put_item(self, Item):
        key = (Item["user_id"], Item["conversation_id"])
        self.items[key] = Item
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    def query(self, KeyConditionExpression=None, ExpressionAttributeValues=None):
        uid = ExpressionAttributeValues.get(":uid")
        result = [item for key, item in self.items.items() if key[0] == uid]
        return {"Items": result}

    def get_item(self, Key):
        key = (Key["user_id"], Key["conversation_id"])
        if key in self.items:
            return {"Item": self.items[key]}
        return {}

    def update_item(
        self, Key=None, UpdateExpression=None, ExpressionAttributeValues=None
    ):
        key = (Key["user_id"], Key["conversation_id"])
        if key not in self.items:
            raise Exception("Not found")

        item = self.items[key]
        if ":msgs" in ExpressionAttributeValues:
            item["messages"] = ExpressionAttributeValues[":msgs"]
        if ":updated" in ExpressionAttributeValues:
            item["updated_at"] = ExpressionAttributeValues[":updated"]

        self.items[key] = item
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    def delete_item(self, Key):
        key = (Key["user_id"], Key["conversation_id"])
        self.items.pop(key, None)
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}


@pytest.fixture(autouse=True)
def patch_table(monkeypatch):
    fake = FakeTable()
    monkeypatch.setattr(svc, "get_table", lambda: fake)
    yield fake


def test_create_get_append_delete_conversation(patch_table):
    client = TestClient(svc.app)

    resp = client.post("/conversations", json={"title": "Test"})
    assert resp.status_code == 200
    payload = resp.json()
    conv_id = payload["id"]
    assert payload["title"] == "Test" or payload["title"].startswith(
        "Conversation-"
    )

    resp = client.get(f"/conversations/{conv_id}")
    assert resp.status_code == 200
    got = resp.json()
    assert got["id"] == conv_id
    assert isinstance(got["messages"], list)

    resp = client.post(
        f"/conversations/{conv_id}/messages",
        json={"role": "user", "content": "hello"},
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert any(message["content"] == "hello" for message in updated["messages"])

    resp = client.get("/conversations")
    assert resp.status_code == 200
    conversations = resp.json()
    assert any(conversation["id"] == conv_id for conversation in conversations)

    resp = client.delete(f"/conversations/{conv_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"
