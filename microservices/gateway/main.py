from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import asyncio
import logging

app = FastAPI()
logging.basicConfig(level=logging.INFO)

# Allow the frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

SERVICE_URLS = {
    "settings": os.getenv("SETTINGS_URL", "http://settings:8001"),
    "conversations": os.getenv("CONVERSATIONS_URL", "http://conversations:8002"),
    "messages": os.getenv("MESSAGES_URL", "http://messages:8003"),
    "ai": os.getenv("AI_URL", "http://ai:8004"),
}


async def proxy_request(method: str, url: str, **kwargs):
    # simple retry logic with backoff for transient DNS/connect errors
    backoff = 0.5
    for attempt in range(3):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.request(method, url, **kwargs)
                resp.raise_for_status()
                try:
                    return resp.json()
                except Exception:
                    return resp.text
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as e:
            logging.warning("proxy_request attempt %d failed for %s: %s", attempt + 1, url, str(e))
            if attempt < 2:
                await asyncio.sleep(backoff)
                backoff *= 2
                continue
            raise HTTPException(status_code=502, detail=f"Upstream service unreachable: {e}")
        except httpx.HTTPStatusError as e:
            # propagate upstream error body if available
            try:
                content = e.response.json()
            except Exception:
                content = e.response.text
            raise HTTPException(status_code=e.response.status_code, detail=content)
        except Exception as e:
            logging.exception("Unexpected proxy error")
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/generate")
async def generate(payload: dict):
    return await proxy_request("POST", f"{SERVICE_URLS['ai']}/generate", json=payload, timeout=30)


@app.post("/api/messages")
async def forward_messages(payload: dict):
    results = {}
    # store in messages service
    results["messages_service"] = await proxy_request("POST", f"{SERVICE_URLS['messages']}/messages", json=payload, timeout=30)

    # if conversation id provided, append to conversation store as well
    conv_id = payload.get("conversation_id")
    if conv_id:
        try:
            results["conversations_service"] = await proxy_request(
                "POST",
                f"{SERVICE_URLS['conversations']}/conversations/{conv_id}/messages",
                json={"role": payload.get("role", "user"), "content": payload.get("message") or payload.get("content")},
                timeout=30,
            )
        except HTTPException as e:
            results["conversations_service"] = {"error": str(e.detail)}

    return results


@app.post("/api/chat/send")
async def send_chat(payload: dict):
    message = payload.get("message", "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    conversation_id = payload.get("conversation_id")

    # Create a conversation if the UI hasn't selected one yet.
    if not conversation_id:
        created = await proxy_request(
            "POST",
            f"{SERVICE_URLS['conversations']}/conversations",
            json={"title": payload.get("title") or "New chat"},
            timeout=30,
        )
        conversation_id = created["id"]

    # Persist user message.
    await proxy_request(
        "POST",
        f"{SERVICE_URLS['messages']}/messages",
        json={"conversation_id": conversation_id, "role": "user", "message": message},
        timeout=30,
    )
    await proxy_request(
        "POST",
        f"{SERVICE_URLS['conversations']}/conversations/{conversation_id}/messages",
        json={"role": "user", "content": message},
        timeout=30,
    )

    # Fetch system prompt and recent history, then ask AI to reply.
    settings = await proxy_request("GET", f"{SERVICE_URLS['settings']}/settings", timeout=30)
    conversation = await proxy_request(
        "GET",
        f"{SERVICE_URLS['conversations']}/conversations/{conversation_id}",
        timeout=30,
    )
    history = conversation.get("messages", [])[-10:]
    history_text = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history)
    prompt = (
        f"System: {settings.get('system_prompt', '')}\n"
        f"Conversation history:\n{history_text}\n"
        f"User: {message}\nAssistant:"
    )

    ai_response = await proxy_request(
        "POST",
        f"{SERVICE_URLS['ai']}/generate",
        json={"prompt": prompt},
        timeout=60,
    )
    assistant_text = ai_response.get("response", {}).get("text", "")

    # Persist assistant message too.
    await proxy_request(
        "POST",
        f"{SERVICE_URLS['messages']}/messages",
        json={"conversation_id": conversation_id, "role": "assistant", "message": assistant_text},
        timeout=30,
    )
    await proxy_request(
        "POST",
        f"{SERVICE_URLS['conversations']}/conversations/{conversation_id}/messages",
        json={"role": "assistant", "content": assistant_text},
        timeout=30,
    )

    updated = await proxy_request(
        "GET",
        f"{SERVICE_URLS['conversations']}/conversations/{conversation_id}",
        timeout=30,
    )

    return {
        "conversation": updated,
        "assistant": {"role": "assistant", "content": assistant_text},
    }


@app.post("/api/conversations")
async def create_conversation(payload: dict):
    return await proxy_request("POST", f"{SERVICE_URLS['conversations']}/conversations", json=payload, timeout=30)


@app.get("/api/settings")
async def get_settings():
    return await proxy_request("GET", f"{SERVICE_URLS['settings']}/settings", timeout=30)


@app.post("/api/settings")
async def post_settings(payload: dict):
    return await proxy_request("POST", f"{SERVICE_URLS['settings']}/settings", json=payload, timeout=30)


@app.get("/api/conversations")
async def get_conversations():
    return await proxy_request("GET", f"{SERVICE_URLS['conversations']}/conversations", timeout=30)


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: int):
    return await proxy_request("GET", f"{SERVICE_URLS['conversations']}/conversations/{conversation_id}", timeout=30)
