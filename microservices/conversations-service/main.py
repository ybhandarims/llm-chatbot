"""
Conversations Service - Manages conversation data in DynamoDB
Uses async architecture with proper error handling and logging
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import json
import logging
import uuid
from datetime import datetime, timezone
import boto3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI()

# Configuration
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "conversations")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)


# Pydantic models
class Message(BaseModel):
    role: str
    content: str


class ConversationCreate(BaseModel):
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: str
    title: str
    messages: List[dict] = []
    created_at: str
    updated_at: str


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "conversations"}


@app.post("/conversations")
def create_conversation(payload: ConversationCreate):
    """Create a new conversation"""
    try:
        conversation_id = str(uuid.uuid4())
        user_id = "default_user"  # In production, extract from JWT
        timestamp = datetime.now(timezone.utc).isoformat()
        
        item = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "title": payload.title or f"Conversation-{timestamp[:10]}",
            "messages": [],
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        
        table.put_item(Item=item)
        logger.info(f"Conversation created: {conversation_id}")
        
        return {
            "id": conversation_id,
            "title": item["title"],
            "messages": [],
            "created_at": timestamp,
            "updated_at": timestamp,
        }
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations")
def list_conversations():
    """List all conversations for user"""
    try:
        user_id = "default_user"  # In production, extract from JWT
        
        response = table.query(
            KeyConditionExpression="user_id = :uid",
            ExpressionAttributeValues={":uid": user_id}
        )
        
        conversations = []
        for item in response.get("Items", []):
            messages = item.get("messages", [])
            last_message = messages[-1]["content"] if messages else None
            
            conversations.append({
                "id": item["conversation_id"],
                "title": item.get("title", "Untitled"),
                "last_message_preview": last_message,
                "created_at": item.get("created_at"),
                "message_count": len(messages),
            })
        
        return conversations
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    """Get specific conversation with all messages"""
    try:
        user_id = "default_user"  # In production, extract from JWT
        
        response = table.get_item(
            Key={
                "user_id": user_id,
                "conversation_id": conversation_id
            }
        )
        
        if "Item" not in response:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        item = response["Item"]
        return {
            "id": conversation_id,
            "title": item.get("title", "Untitled"),
            "messages": item.get("messages", []),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/conversations/{conversation_id}/messages")
def append_message(conversation_id: str, payload: Message):
    """Append a message to a conversation"""
    try:
        user_id = "default_user"  # In production, extract from JWT
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Get current conversation
        response = table.get_item(
            Key={
                "user_id": user_id,
                "conversation_id": conversation_id
            }
        )
        
        if "Item" not in response:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        item = response["Item"]
        messages = item.get("messages", [])
        
        # Add new message
        new_message = {
            "role": payload.role,
            "content": payload.content,
            "timestamp": timestamp,
        }
        messages.append(new_message)
        
        # Update conversation
        table.update_item(
            Key={
                "user_id": user_id,
                "conversation_id": conversation_id
            },
            UpdateExpression="SET messages = :msgs, updated_at = :updated",
            ExpressionAttributeValues={
                ":msgs": messages,
                ":updated": timestamp
            }
        )
        
        logger.info(f"Message added to conversation {conversation_id}")
        
        return {
            "id": conversation_id,
            "messages": messages,
            "updated_at": timestamp,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error appending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    try:
        user_id = "default_user"  # In production, extract from JWT
        
        table.delete_item(
            Key={
                "user_id": user_id,
                "conversation_id": conversation_id
            }
        )
        
        logger.info(f"Conversation deleted: {conversation_id}")
        return {"status": "deleted", "conversation_id": conversation_id}
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
