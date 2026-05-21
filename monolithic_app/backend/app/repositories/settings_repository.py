from __future__ import annotations

from datetime import datetime, timezone

from app.core.database import get_connection


ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"



def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime(ISO_FORMAT)


class SettingsRepository:
    def get_value(self, key: str) -> str | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return str(row["value"])

    def upsert_value(self, key: str, value: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, value, _now_iso()),
            )
