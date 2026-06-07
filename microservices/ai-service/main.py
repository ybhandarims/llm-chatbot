from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import httpx
import os
import asyncio
import json
import uuid
import logging
import boto3
from datetime import datetime, timezone

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

SERVICE_URLS = {
    "settings": os.getenv("SETTINGS_URL", "http://settings:8001"),
    "conversations": os.getenv("CONVERSATIONS_URL", "http://conversations:8002"),
    "messages": os.getenv("MESSAGES_URL", "http://messages:8003"),
}

# AWS Configuration
SQS_QUEUE_URL = os.getenv(
    "SQS_QUEUE_URL", "http://localstack:4566/000000000000/ai-jobs"
)
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# SQS client
sqs_client = boto3.client("sqs", region_name=AWS_REGION)


class ChatMessage(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    title: Optional[str] = None


class SettingsUpdate(BaseModel):
    system_prompt: Optional[str] = None
    model: Optional[str] = None


async def proxy_request(method: str, url: str, **kwargs):
    """Proxy request with retry logic and backoff"""
    backoff = 0.5
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.request(method, url, **kwargs)
                resp.raise_for_status()
                try:
                    return resp.json()
                except Exception:
                    return resp.text
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as e:
            logger.warning(f"Proxy attempt {attempt + 1} failed for {url}: {e}")
            if attempt < 2:
                await asyncio.sleep(backoff)
                backoff *= 2
                continue
            raise HTTPException(status_code=502, detail=f"Service unreachable: {e}")
        except httpx.HTTPStatusError as e:
            try:
                content = e.response.json()
            except Exception:
                content = e.response.text
            raise HTTPException(status_code=e.response.status_code, detail=content)
        except Exception as e:
            logger.exception("Proxy error")
            raise HTTPException(status_code=500, detail=str(e))


def send_to_sqs(job_data: dict) -> str:
    """Send job to SQS for async processing"""
    job_id = str(uuid.uuid4())
    message = {
        "job_id": job_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **job_data,
    }

    try:
        response = sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message),
            MessageGroupId=job_data.get("conversation_id", "default"),
        )
        logger.info(f"Job {job_id} sent to SQS: {response['MessageId']}")
        return job_id
    except Exception as e:
        logger.error(f"Error sending to SQS: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue AI job")


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "ai-worker"}


# CRUD Operations for Settings
@app.get("/api/settings")
async def get_settings():
    """Get user settings"""
    try:
        return await proxy_request(
            "GET", f"{SERVICE_URLS['settings']}/settings", timeout=30
        )
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        raise


@app.post("/api/settings")
async def update_settings(payload: SettingsUpdate):
    """Update user settings"""
    try:
        return await proxy_request(
            "POST",
            f"{SERVICE_URLS['settings']}/settings",
            json=payload.dict(),
            timeout=30,
        )
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise


# CRUD Operations for Conversations
@app.get("/api/conversations")
async def get_conversations():
    """List all conversations for user"""
    try:
        return await proxy_request(
            "GET", f"{SERVICE_URLS['conversations']}/conversations", timeout=30
        )
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        raise


@app.post("/api/conversations")
async def create_conversation(payload: dict):
    """Create new conversation"""
    try:
        return await proxy_request(
            "POST",
            f"{SERVICE_URLS['conversations']}/conversations",
            json=payload,
            timeout=30,
        )
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get specific conversation"""
    try:
        return await proxy_request(
            "GET",
            f"{SERVICE_URLS['conversations']}/conversations/{conversation_id}",
            timeout=30,
        )
    except Exception as e:
        logger.error(f"Error fetching conversation: {e}")
        raise


@app.post("/api/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    """Get messages in conversation"""
    try:
        return await proxy_request(
            "GET",
            f"{SERVICE_URLS['messages']}/conversations/{conversation_id}",
            timeout=30,
        )
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        raise


# Async Chat Flow with SQS
@app.post("/api/chat/send")
async def send_chat_message(payload: ChatMessage, background_tasks: BackgroundTasks):
    """
    Send chat message - NEW ASYNC ARCHITECTURE

    Flow:
    1. Validate message
    2. Create/get conversation
    3. Store user message
    4. Send job to SQS for async AI processing
    5. Return immediately

    Benefits:
    - Better scalability
    - Better user experience (no blocking)
    - Queue buffering
    - Retry capability
    """

    try:
        message = payload.message.strip()
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        conversation_id = payload.conversation_id

        # Create conversation if needed
        if not conversation_id:
            conv_payload = {"title": payload.title or "New Chat"}
            created = await proxy_request(
                "POST",
                f"{SERVICE_URLS['conversations']}/conversations",
                json=conv_payload,
                timeout=30,
            )
            conversation_id = created.get("id", str(uuid.uuid4()))

        # Store user message immediately
        message_record = {
            "conversation_id": conversation_id,
            "role": "user",
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await proxy_request(
            "POST",
            f"{SERVICE_URLS['messages']}/messages",
            json=message_record,
            timeout=30,
        )

        # Send AI job to SQS (async processing)
        job_id = send_to_sqs(
            {
                "conversation_id": conversation_id,
                "message": message,
                "type": "ai_generate",
            }
        )

        return {
            "status": "accepted",
            "conversation_id": conversation_id,
            "job_id": job_id,
            "message": "Your message is being processed. The AI response will appear shortly.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/job/{job_id}")
async def get_job_status(job_id: str):
    """Check status of AI job (optional polling endpoint)"""
    try:
        # In production, check job status from database
        return {"job_id": job_id, "status": "processing"}
    except Exception as e:
        logger.error(f"Error checking job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Admin/Debug Endpoints
@app.get("/api/debug/queue-stats")
async def queue_stats():
    """Get SQS queue statistics"""
    try:
        attrs = sqs_client.get_queue_attributes(
            QueueUrl=SQS_QUEUE_URL,
            AttributeNames=[
                "ApproximateNumberOfMessages",
                "ApproximateNumberOfMessagesNotVisible",
            ],
        )
        return {
            "queue_url": SQS_QUEUE_URL,
            "approximate_messages": attrs["Attributes"].get(
                "ApproximateNumberOfMessages", 0
            ),
            "processing": attrs["Attributes"].get(
                "ApproximateNumberOfMessagesNotVisible", 0
            ),
        }
    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
