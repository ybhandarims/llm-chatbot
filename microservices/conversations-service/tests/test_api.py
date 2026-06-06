import sys
import os
import pytest
from fastapi.testclient import TestClient

# Make the service importable by adding its parent directory to sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import main as svc


class FakeTable:
    def __init__(self):
        # store items keyed by (user_id, conversation_id)
        self.items = {}

    def put_item(self, Item):
        key = (Item["user_id"], Item["conversation_id"])
        self.items[key] = Item

    def query(self, KeyConditionExpression=None, ExpressionAttributeValues=None):
        uid = ExpressionAttributeValues.get(":uid")
        result = [v for k, v in self.items.items() if k[0] == uid]
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
        # simplistic handling: replace messages and updated_at
        if ":msgs" in ExpressionAttributeValues:
            item["messages"] = ExpressionAttributeValues[":msgs"]
        if ":updated" in ExpressionAttributeValues:
            item["updated_at"] = ExpressionAttributeValues[":updated"]
        self.items[key] = item

    def delete_item(self, Key):
        key = (Key["user_id"], Key["conversation_id"])
        self.items.pop(key, None)


@pytest.fixture(autouse=True)
def patch_table(monkeypatch):
    fake = FakeTable()
    # replace the DynamoDB table used in the service with our fake
    svc.table = fake
    yield fake


def test_create_get_append_delete_conversation(patch_table):
    client = TestClient(svc.app)

    # create
    resp = client.post("/conversations", json={"title": "Test"})
    assert resp.status_code == 200
    payload = resp.json()
    conv_id = payload["id"]
    assert payload["title"] == "Test" or payload["title"].startswith("Conversation-")

    # get
    resp = client.get(f"/conversations/{conv_id}")
    assert resp.status_code == 200
    got = resp.json()
    assert got["id"] == conv_id
    assert isinstance(got["messages"], list)

    # append message
    resp = client.post(
        f"/conversations/{conv_id}/messages", json={"role": "user", "content": "hello"}
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert any(m["content"] == "hello" for m in updated["messages"])

    # list
    resp = client.get("/conversations")
    assert resp.status_code == 200
    lst = resp.json()
    assert any(c["id"] == conv_id for c in lst)

    # delete
    resp = client.delete(f"/conversations/{conv_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"
