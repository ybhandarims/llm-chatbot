import os
import sys
from typing import Optional

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import main


class FakeRedis:
    def __init__(self):
        self.data = {}

    def ping(self):
        return True

    def exists(self, key: str):
        return key in self.data

    def hset(self, key: str, mapping=None):
        if mapping is None:
            mapping = {}
        self.data[key] = {k: str(v) for k, v in mapping.items()}

    def hgetall(self, key: str):
        return self.data.get(key, {})

    def sadd(self, key: str, *values):
        current = self.data.get(key, set())
        if not isinstance(current, set):
            current = set(current)
        current.update(values)
        self.data[key] = current
        return len(values)

    def smembers(self, key: str):
        return self.data.get(key, set())

    def expire(self, key: str, seconds: int):
        return True

    def delete(self, *keys):
        for key in keys:
            self.data.pop(key, None)


def test_login_refresh_logout(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(main, "redis_client", fake_redis)
    monkeypatch.setattr(main, "hash_password", lambda password: password)
    monkeypatch.setattr(main, "verify_password", lambda password, password_hash: password == password_hash)
    main.ensure_role("admin", ["auth:manage", "users:manage", "roles:manage", "chat:send", "settings:read", "settings:write", "conversations:read", "messages:read", "messages:write"])
    main.ensure_role("user", ["chat:send", "conversations:read", "messages:write", "settings:read"])
    main.ensure_default_admin()

    with TestClient(main.app) as client:
        response = client.post("/api/login", json={"username": "admin", "password": "admin123"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["roles"] == ["admin"]

        access_token = data["access_token"]
        refresh_token = data["refresh_token"]

        auth_response = client.post(
            "/api/authorize",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"permission": "chat:send"},
        )
        assert auth_response.status_code == 200
        assert auth_response.json()["allowed"] is True

        refresh_response = client.post(
            "/api/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        assert refresh_data["access_token"] != access_token
        assert refresh_data["refresh_token"] != refresh_token

        old_auth_response = client.post(
            "/api/authorize",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"permission": "chat:send"},
        )
        assert old_auth_response.status_code == 401

        new_access_token = refresh_data["access_token"]
        logout_response = client.post(
            "/api/logout",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert logout_response.status_code == 200
        assert logout_response.json()["detail"] == "Logged out"

        post_logout_response = client.post(
            "/api/authorize",
            headers={"Authorization": f"Bearer {new_access_token}"},
            json={"permission": "chat:send"},
        )
        assert post_logout_response.status_code == 401
