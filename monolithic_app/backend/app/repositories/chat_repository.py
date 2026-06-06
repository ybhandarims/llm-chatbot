from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.database import get_connection


ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime(ISO_FORMAT)


def _to_dt(value: str) -> datetime:
    return datetime.strptime(value, ISO_FORMAT).replace(tzinfo=timezone.utc)


class ChatRepository:
    def create_conversation(self, title: str) -> dict[str, Any]:
        now = _now_iso()
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO conversations (title, created_at, updated_at) VALUES (?, ?, ?)",
                (title, now, now),
            )
            conversation_id = int(cursor.lastrowid)
        return self.get_conversation_summary(conversation_id)

    def touch_conversation(self, conversation_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (_now_iso(), conversation_id),
            )

    def get_conversation_summary(self, conversation_id: int) -> dict[str, Any]:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT c.id, c.title, c.created_at, c.updated_at,
                    (
                        SELECT m.content
                        FROM messages m
                        WHERE m.conversation_id = c.id
                        ORDER BY m.id DESC
                        LIMIT 1
                    ) AS last_message_preview
                FROM conversations c
                WHERE c.id = ?
                """,
                (conversation_id,),
            ).fetchone()
        if row is None:
            raise ValueError("Conversation not found")
        return {
            "id": int(row["id"]),
            "title": row["title"],
            "created_at": _to_dt(row["created_at"]),
            "updated_at": _to_dt(row["updated_at"]),
            "last_message_preview": row["last_message_preview"],
        }

    def list_conversations(self) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT c.id, c.title, c.created_at, c.updated_at,
                    (
                        SELECT m.content
                        FROM messages m
                        WHERE m.conversation_id = c.id
                        ORDER BY m.id DESC
                        LIMIT 1
                    ) AS last_message_preview
                FROM conversations c
                ORDER BY c.updated_at DESC
                """
            ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "title": row["title"],
                "created_at": _to_dt(row["created_at"]),
                "updated_at": _to_dt(row["updated_at"]),
                "last_message_preview": row["last_message_preview"],
            }
            for row in rows
        ]

    def add_message(
        self, conversation_id: int, role: str, content: str
    ) -> dict[str, Any]:
        now = _now_iso()
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, role, content, now),
            )
            message_id = int(cursor.lastrowid)
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
        return {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "created_at": _to_dt(now),
        }

    def get_messages(self, conversation_id: int) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, conversation_id, role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (conversation_id,),
            ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "conversation_id": int(row["conversation_id"]),
                "role": row["role"],
                "content": row["content"],
                "created_at": _to_dt(row["created_at"]),
            }
            for row in rows
        ]

    def get_conversation_detail(self, conversation_id: int) -> dict[str, Any]:
        summary = self.get_conversation_summary(conversation_id)
        messages = self.get_messages(conversation_id)
        return {
            "id": summary["id"],
            "title": summary["title"],
            "created_at": summary["created_at"],
            "updated_at": summary["updated_at"],
            "messages": messages,
        }
