from fastapi import FastAPI, HTTPException
import sqlite3
import os
from datetime import datetime

app = FastAPI()

DB_PATH = os.getenv("MESSAGES_DB", "./messages.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/messages")
def post_message(payload: dict):
    conv_id = payload.get("conversation_id")
    role = payload.get("role", "user")
    content = payload.get("message") or payload.get("content")
    if content is None:
        raise HTTPException(status_code=400, detail="message/content required")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (conv_id, role, content, datetime.utcnow().isoformat()),
    )
    conn.commit()
    mid = cur.lastrowid
    conn.close()
    return {"status": "ok", "id": mid, "conversation_id": conv_id, "role": role, "content": content}


@app.get("/messages")
def list_messages():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, conversation_id, role, content, created_at FROM messages ORDER BY id ASC")
    rows = cur.fetchall()
    out = []
    for r in rows:
        out.append({"id": r["id"], "conversation_id": r["conversation_id"], "role": r["role"], "content": r["content"], "created_at": r["created_at"]})
    conn.close()
    return out
