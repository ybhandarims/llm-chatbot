from fastapi import FastAPI
from typing import List

app = FastAPI()

from fastapi import FastAPI, HTTPException
import sqlite3
import os
import json
from datetime import datetime

app = FastAPI()

DB_PATH = os.getenv("CONVERSATIONS_DB", "./conversations.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            messages TEXT
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


@app.get("/conversations")
def list_conversations():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, title, messages FROM conversations ORDER BY id DESC")
    rows = cur.fetchall()
    out = []
    for r in rows:
        msgs = json.loads(r["messages"]) if r["messages"] else []
        preview = msgs[-1]["content"] if msgs else None
        out.append({"id": r["id"], "title": r["title"], "last_message_preview": preview})
    conn.close()
    return out


@app.post("/conversations")
def create_conversation(payload: dict):
    title = payload.get("title") or f"conv-{int(datetime.utcnow().timestamp())}"
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO conversations (title, messages) VALUES (?, ?)", (title, json.dumps([])))
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return {"id": cid, "title": title, "messages": []}


@app.get("/conversations/{conv_id}")
def get_conversation(conv_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, title, messages FROM conversations WHERE id = ?", (conv_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="conversation not found")
    msgs = json.loads(row["messages"]) if row["messages"] else []
    return {"id": row["id"], "title": row["title"], "messages": msgs}


@app.post("/conversations/{conv_id}/messages")
def append_message(conv_id: int, payload: dict):
    role = payload.get("role", "user")
    content = payload.get("content")
    if content is None:
        raise HTTPException(status_code=400, detail="content is required")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT messages FROM conversations WHERE id = ?", (conv_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="conversation not found")
    msgs = json.loads(row["messages"]) if row["messages"] else []
    msg = {"role": role, "content": content, "ts": datetime.utcnow().isoformat()}
    msgs.append(msg)
    cur.execute("UPDATE conversations SET messages = ? WHERE id = ?", (json.dumps(msgs), conv_id))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": msg}
