"""
AI Worker Service - Processes async AI jobs from SQS queue
This is part of the new async architecture for scalability
"""

import os
import json
import logging
import asyncio
import httpx
from datetime import datetime
import boto3
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-test")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
OPENAI_MOCK = os.getenv("OPENAI_MOCK", "true").lower() == "true"
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "You are a helpful assistant.")

SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "http://localstack:4566/000000000000/ai-jobs")
DLQ_URL = os.getenv("DLQ_URL", "http://localstack:4566/000000000000/ai-jobs-dlq")
MESSAGES_SERVICE_URL = os.getenv("MESSAGES_SERVICE_URL", "http://messages:8003")
CONVERSATIONS_SERVICE_URL = os.getenv("CONVERSATIONS_SERVICE_URL", "http://conversations:8002")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Initialize AWS clients
sqs_client = boto3.client('sqs', region_name=AWS_REGION)

# Initialize OpenAI client
openai_client = None
if not OPENAI_MOCK:
    if OPENAI_API_KEY and OPENAI_API_KEY != "sk-test":
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    else:
        logger.warning("OpenAI API key not configured, using mock responses")


class AIWorker:
    """Worker that processes AI jobs from SQS"""
    
    def __init__(self):
        self.running = False
        self.max_retries = 3
    
    async def process_message(self, message: dict) -> bool:
        """
        Process a single AI job message
        Returns True if successful, False if should retry
        """
        try:
            job_id = message.get('job_id')
            message_id = message.get('ReceiptHandle')
            
            logger.info(f"Processing job {job_id}")
            
            # Parse message body
            body = json.loads(message.get('Body', '{}'))
            conversation_id = body.get('conversation_id')
            user_message = body.get('message')
            
            if not conversation_id or not user_message:
                logger.error(f"Invalid job data: {body}")
                return False
            
            # Fetch conversation history
            history = await self._get_conversation_history(conversation_id)
            
            # Generate AI response
            ai_response = await self._generate_response(user_message, history)
            
            if not ai_response:
                logger.error(f"Failed to generate response for job {job_id}")
                return False
            
            # Store AI response
            success = await self._store_message(
                conversation_id,
                "assistant",
                ai_response
            )
            
            if not success:
                logger.error(f"Failed to store AI response for job {job_id}")
                return False
            
            # Delete message from queue
            sqs_client.delete_message(
                QueueUrl=SQS_QUEUE_URL,
                ReceiptHandle=message_id
            )
            
            logger.info(f"Successfully processed job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return False
    
    async def _get_conversation_history(self, conversation_id: str) -> list:
        """Fetch conversation history"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{CONVERSATIONS_SERVICE_URL}/conversations/{conversation_id}"
                )
                if resp.status_code == 200:
                    return resp.json().get('messages', [])[-10:]
            return []
        except Exception as e:
            logger.error(f"Error fetching conversation history: {e}")
            return []
    
    async def _generate_response(self, user_message: str, history: list) -> str:
        """Generate AI response"""
        try:
            if OPENAI_MOCK:
                logger.info("Using mock AI response")
                return f"Echo: {user_message}"
            
            if not openai_client:
                logger.warning("OpenAI client not initialized, using mock response")
                return f"I received your message: '{user_message}'"
            
            # Build messages
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
            ]
            
            # Add conversation history
            for msg in history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", msg.get("message", ""))
                })
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Call OpenAI
            response = await asyncio.to_thread(
                openai_client.chat.completions.create,
                model=OPENAI_MODEL,
                messages=messages,
                max_tokens=512,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return None
    
    async def _store_message(self, conversation_id: str, role: str, content: str) -> bool:
        """Store message in messages service"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{MESSAGES_SERVICE_URL}/messages",
                    json={
                        "conversation_id": conversation_id,
                        "role": role,
                        "message": content,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error storing message: {e}")
            return False
    
    async def _send_to_dlq(self, message: dict):
        """Send message to Dead Letter Queue"""
        try:
            dlq_body = json.loads(message.get('Body', '{}'))
            dlq_body['failed_at'] = datetime.utcnow().isoformat()
            dlq_body['reason'] = 'Max retries exceeded'
            
            sqs_client.send_message(
                QueueUrl=DLQ_URL,
                MessageBody=json.dumps(dlq_body),
                MessageGroupId=dlq_body.get('conversation_id', 'default')
            )
            logger.info("Message sent to DLQ")
        except Exception as e:
            logger.error(f"Error sending to DLQ: {e}")
    
    async def run(self):
        """Main worker loop"""
        self.running = True
        logger.info("AI Worker started, listening for jobs...")
        
        while self.running:
            try:
                # Poll SQS
                messages = sqs_client.receive_message(
                    QueueUrl=SQS_QUEUE_URL,
                    MaxNumberOfMessages=1,
                    WaitTimeSeconds=20
                ).get('Messages', [])
                
                for message in messages:
                    success = await self.process_message(message)
                    
                    if not success:
                        # Increment retry count
                        body = json.loads(message.get('Body', '{}'))
                        retry_count = body.get('retry_count', 0) + 1
                        
                        if retry_count >= self.max_retries:
                            logger.error(f"Max retries exceeded for job {body.get('job_id')}")
                            await self._send_to_dlq(message)
                            # Delete from main queue
                            sqs_client.delete_message(
                                QueueUrl=SQS_QUEUE_URL,
                                ReceiptHandle=message.get('ReceiptHandle')
                            )
                        else:
                            # Leave in queue for retry (visibility timeout)
                            logger.info(f"Retrying job {body.get('job_id')} (attempt {retry_count})")
                
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(5)
    
    def stop(self):
        """Stop the worker"""
        self.running = False
        logger.info("AI Worker stopped")


# Global worker instance
worker = AIWorker()


# Optional: FastAPI endpoints for health checks
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "ai-worker"}


@app.on_event("startup")
async def startup():
    """Start worker when app starts"""
    # Run worker in background
    asyncio.create_task(worker.run())


@app.on_event("shutdown")
async def shutdown():
    """Stop worker when app shuts down"""
    worker.stop()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
