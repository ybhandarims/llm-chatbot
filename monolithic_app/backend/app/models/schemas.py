from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Role = Literal["system", "user", "assistant"]


class HealthResponse(BaseModel):
    status: str


class MessageOut(BaseModel):
    id: int
    conversation_id: int
    role: Role
    content: str
    created_at: datetime


class ConversationSummary(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    last_message_preview: str | None = None


class ConversationDetail(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut]


class SendMessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=6000)
    conversation_id: int | None = None


class SendMessageOut(BaseModel):
    conversation: ConversationSummary
    user_message: MessageOut
    assistant_message: MessageOut


class SystemPromptOut(BaseModel):
    system_prompt: str


class SystemPromptUpdateIn(BaseModel):
    system_prompt: str = Field(min_length=1, max_length=4000)
