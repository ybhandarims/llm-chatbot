@'
"""
AI Worker Service - Processes async AI jobs from SQS queue
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import boto3
import httpx
from fastapi import FastAPI
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-test")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
OPENAI_MOCK = os.getenv("OPENAI_MOCK", "true").lower() == "true"
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "You are a helpful assistant.")

SQS_QUEUE_URL = os.getenv(
    "SQS_QUEUE_URL", "http://localstack:4566/000000000000/ai-jobs"
)
DLQ_URL = os.getenv("DLQ_URL", "http://localstack:4566/000000000000/ai-jobs-dlq")
MESSAGES_SERVICE_URL = os.getenv("MESSAGES_SERVICE_URL", "http://messages:8003")
CONVERSATIONS_SERVICE_URL = os.getenv(
    "CONVERSATIONS_SERVICE_URL", "http://conversations:8002"
)
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

sqs_client = boto3.client("sqs", region_name=AWS_REGION)

openai_client = None
if not OPENAI_MOCK and OPENAI_API_KEY and OPENAI_API_KEY != "sk-test":
    openai_client = OpenAI(api_key=OPENAI_API_KEY)


class AIWorker:
    def __init__(self):
        self.running = False
        self.max_retries = 3

    async def process_message(self, message: dict) -> bool:
        try:
            job_id = message.get("job_id")
            message_id = message.get("ReceiptHandle")

            logger.info("Processing job %s", job_id)

            body = json.loads(message.get("Body", "{}"))
            conversation_id = body.get("conversation_id")
            user_message = body.get("message")

            if not conversation_id or not user_message:
                logger.error("Invalid job data: %s", body)
                return False

            history = await self._get_conversation_history(conversation_id)
            ai_response = await self._generate_response(user_message, history)

            if not ai_response:
                logger.error("Failed to generate response for job %s", job_id)
                return False

            success = await self._store_message(conversation_id, "assistant", ai_response)
            if not success:
                logger.error("Failed to store AI response for job %s", job_id)
                return False

            sqs_client.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=message_id)

            logger.info("Successfully processed job %s", job_id)
            return True

        except Exception as e:
            logger.error("Error processing message: %s", e)
            return False

    async def _get_conversation_history(self, conversation_id: str) -> list:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{CONVERSATIONS_SERVICE_URL}/conversations/{conversation_id}"
                )
                if resp.status_code == 200:
                    return resp.json().get("messages", [])[-10:]
            return []
        except Exception as e:
            logger.error("Error fetching conversation history: %s", e)
            return []

    async def _generate_response(self, user_message: str, history: list) -> str:
        try:
            if OPENAI_MOCK:
                return f"Echo: {user_message}"

            if not openai_client:
                return f"I received your message: '{user_message}'"

            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            for msg in history:
                messages.append(
                    {
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", msg.get("message", "")),
                    }
                )
            messages.append({"role": "user", "content": user_message})

            def _create_completion():
                return openai_client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    max_tokens=512,
                    temperature=0.7,
                )

            response = await asyncio.to_thread(_create_completion)
            content = response.choices[0].message.content
            return content or ""

        except Exception as e:
            logger.error("Error generating response: %s", e)
            return ""

    async def _store_message(self, conversation_id: str, role: str, content: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{MESSAGES_SERVICE_URL}/messages",
                    json={
                        "conversation_id": conversation_id,
                        "role": role,
                        "message": content,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                return response.status_code == 200
        except Exception as e:
            logger.error("Error storing message: %s", e)
            return False

    async def _send_to_dlq(self, message: dict):
        try:
            dlq_body = json.loads(message.get("Body", "{}"))
            dlq_body["failed_at"] = datetime.now(timezone.utc).isoformat()
            dlq_body["reason"] = "Max retries exceeded"

            sqs_client.send_message(
                QueueUrl=DLQ_URL,
                MessageBody=json.dumps(dlq_body),
                MessageGroupId=dlq_body.get("conversation_id", "default"),
            )
            logger.info("Message sent to DLQ")
        except Exception as e:
            logger.error("Error sending to DLQ: %s", e)

    async def run(self):
        self.running = True
        logger.info("AI Worker started, listening for jobs...")

        while self.running:
            try:
                messages = sqs_client.receive_message(
                    QueueUrl=SQS_QUEUE_URL, MaxNumberOfMessages=1, WaitTimeSeconds=20
                ).get("Messages", [])

                for message in messages:
                    success = await self.process_message(message)

                    if not success:
                        body = json.loads(message.get("Body", "{}"))
                        retry_count = body.get("retry_count", 0) + 1

                        if retry_count >= self.max_retries:
                            logger.error("Max retries exceeded for job %s", body.get("job_id"))
                            await self._send_to_dlq(message)
                            sqs_client.delete_message(
                                QueueUrl=SQS_QUEUE_URL,
                                ReceiptHandle=message.get("ReceiptHandle"),
                            )
                        else:
                            logger.info(
                                "Retrying job %s (attempt %s)",
                                body.get("job_id"),
                                retry_count,
                            )

            except Exception as e:
                logger.error("Error in worker loop: %s", e)
                await asyncio.sleep(5)

    def stop(self):
        self.running = False
        logger.info("AI Worker stopped")


worker = AIWorker()


@asynccontextmanager
async def lifespan(app):
    worker_task = asyncio.create_task(worker.run())
    try:
        yield
    finally:
        worker.stop()
        if not worker_task.done():
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-worker"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
