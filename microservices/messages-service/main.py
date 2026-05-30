"""
Messages Service - Manages individual messages in DynamoDB
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
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "messages")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)


# Pydantic models
class MessageCreate(BaseModel):
    conversation_id: str
    role: str
    message: str


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    message: str
    timestamp: str


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "messages"}


@app.post("/messages")
def create_message(payload: MessageCreate):
    """Create a new message"""
    try:
        message_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        item = {
            "conversation_id": payload.conversation_id,
            "message_id": message_id,
            "role": payload.role,
            "message": payload.message,
            "timestamp": timestamp,
        }
        
        table.put_item(Item=item)
        logger.info(f"Message created: {message_id}")
        
        return {
            "id": message_id,
            "conversation_id": payload.conversation_id,
            "role": payload.role,
            "message": payload.message,
            "timestamp": timestamp,
        }
    except Exception as e:
        logger.error(f"Error creating message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations/{conversation_id}")
def get_conversation_messages(conversation_id: str):
    """Get all messages for a conversation"""
    try:
        response = table.query(
            KeyConditionExpression="conversation_id = :cid",
            ExpressionAttributeValues={":cid": conversation_id},
            ScanIndexForward=True  # Sort by timestamp ascending
        )
        
        messages = []
        for item in response.get("Items", []):
            messages.append({
                "id": item["message_id"],
                "conversation_id": conversation_id,
                "role": item.get("role"),
                "message": item.get("message"),
                "content": item.get("message"),  # Alias for compatibility
                "timestamp": item.get("timestamp"),
            })
        
        return messages
    except Exception as e:
        logger.error(f"Error getting conversation messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/messages/{message_id}")
def get_message(message_id: str):
    """Get a specific message"""
    try:
        # Scan for the message (inefficient in production, should use GSI)
        response = table.scan(
            FilterExpression="message_id = :mid",
            ExpressionAttributeValues={":mid": message_id}
        )
        
        items = response.get("Items", [])
        if not items:
            raise HTTPException(status_code=404, detail="Message not found")
        
        item = items[0]
        return {
            "id": message_id,
            "conversation_id": item.get("conversation_id"),
            "role": item.get("role"),
            "message": item.get("message"),
            "timestamp": item.get("timestamp"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/messages/{message_id}")
def delete_message(message_id: str):
    """Delete a message (soft delete recommended in production)"""
    try:
        # Scan to find and delete
        response = table.scan(
            FilterExpression="message_id = :mid",
            ExpressionAttributeValues={":mid": message_id}
        )
        
        items = response.get("Items", [])
        if not items:
            raise HTTPException(status_code=404, detail="Message not found")
        
        item = items[0]
        table.delete_item(
            Key={
                "conversation_id": item["conversation_id"],
                "message_id": message_id
            }
        )
        
        logger.info(f"Message deleted: {message_id}")
        return {"status": "deleted", "message_id": message_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/messages/{message_id}/update")
def update_message(message_id: str, payload: dict):
    """Update a message"""
    try:
        # Scan to find message
        response = table.scan(
            FilterExpression="message_id = :mid",
            ExpressionAttributeValues={":mid": message_id}
        )
        
        items = response.get("Items", [])
        if not items:
            raise HTTPException(status_code=404, detail="Message not found")
        
        item = items[0]
        timestamp = datetime.now(timezone.utc).isoformat()
        
        table.update_item(
            Key={
                "conversation_id": item["conversation_id"],
                "message_id": message_id
            },
            UpdateExpression="SET #msg = :m, updated_at = :upd",
            ExpressionAttributeNames={"#msg": "message"},
            ExpressionAttributeValues={
                ":m": payload.get("message"),
                ":upd": timestamp
            }
        )
        
        logger.info(f"Message updated: {message_id}")
        return {"status": "updated", "message_id": message_id, "timestamp": timestamp}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating message: {e}")
        raise HTTPException(status_code=500, detail=str(e))
