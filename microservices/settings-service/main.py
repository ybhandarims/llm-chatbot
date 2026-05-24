"""
Settings Service - Manages user settings in DynamoDB
Uses async architecture with proper error handling and logging
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import logging
import boto3
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI()

# Configuration
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "settings")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)


# Pydantic models
class SettingsUpdate(BaseModel):
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


# Default settings
DEFAULT_SETTINGS = {
    "system_prompt": "You are a helpful assistant.",
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "max_tokens": 512,
}


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "settings"}


@app.get("/settings")
def get_settings():
    """Get user settings"""
    try:
        user_id = "default_user"  # In production, extract from JWT
        
        response = table.get_item(
            Key={
                "user_id": user_id,
                "setting_key": "preferences"
            }
        )
        
        if "Item" not in response:
            # Return default settings
            return DEFAULT_SETTINGS
        
        item = response["Item"]
        settings = {
            "system_prompt": item.get("system_prompt", DEFAULT_SETTINGS["system_prompt"]),
            "model": item.get("model", DEFAULT_SETTINGS["model"]),
            "temperature": item.get("temperature", DEFAULT_SETTINGS["temperature"]),
            "max_tokens": item.get("max_tokens", DEFAULT_SETTINGS["max_tokens"]),
        }
        
        return settings
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        # Return defaults on error
        return DEFAULT_SETTINGS


@app.post("/settings")
def update_settings(payload: SettingsUpdate):
    """Update user settings"""
    try:
        user_id = "default_user"  # In production, extract from JWT
        timestamp = datetime.utcnow().isoformat()
        
        # Get current settings
        current_settings = get_settings()
        
        # Update with provided values
        updates = {k: v for k, v in payload.dict().items() if v is not None}
        
        item = {
            "user_id": user_id,
            "setting_key": "preferences",
            "system_prompt": updates.get("system_prompt", current_settings.get("system_prompt")),
            "model": updates.get("model", current_settings.get("model")),
            "temperature": updates.get("temperature", current_settings.get("temperature")),
            "max_tokens": updates.get("max_tokens", current_settings.get("max_tokens")),
            "updated_at": timestamp,
        }
        
        table.put_item(Item=item)
        logger.info(f"Settings updated for user {user_id}")
        
        return {
            "status": "updated",
            "settings": {
                "system_prompt": item["system_prompt"],
                "model": item["model"],
                "temperature": item["temperature"],
                "max_tokens": item["max_tokens"],
            },
            "updated_at": timestamp,
        }
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/settings/reset")
def reset_settings():
    """Reset settings to defaults"""
    try:
        user_id = "default_user"  # In production, extract from JWT
        timestamp = datetime.utcnow().isoformat()
        
        item = {
            "user_id": user_id,
            "setting_key": "preferences",
            **DEFAULT_SETTINGS,
            "updated_at": timestamp,
        }
        
        table.put_item(Item=item)
        logger.info(f"Settings reset for user {user_id}")
        
        return {
            "status": "reset",
            "settings": DEFAULT_SETTINGS,
            "updated_at": timestamp,
        }
    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/settings/model-options")
def get_model_options():
    """Get available model options"""
    return {
        "models": [
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo",
            "claude-3-opus",
            "claude-3-sonnet",
            "local-mock"
        ],
        "temperature_range": [0.0, 2.0],
        "max_tokens_range": [1, 4096],
    }
