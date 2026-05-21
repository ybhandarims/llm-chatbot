from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    ConversationDetail,
    ConversationSummary,
    HealthResponse,
    SendMessageIn,
    SendMessageOut,
    SystemPromptOut,
    SystemPromptUpdateIn,
)
from app.repositories.chat_repository import ChatRepository
from app.repositories.settings_repository import SettingsRepository
from app.services.chat_service import ChatService
from app.services.openai_service import OpenAIService


router = APIRouter(prefix="/api", tags=["api"])

_chat_repository = ChatRepository()
_settings_repository = SettingsRepository()
_openai_service = OpenAIService()
_chat_service = ChatService(
    chat_repository=_chat_repository,
    settings_repository=_settings_repository,
    openai_service=_openai_service,
)


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations() -> list[ConversationSummary]:
    return [ConversationSummary(**item) for item in _chat_repository.list_conversations()]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: int) -> ConversationDetail:
    try:
        detail = _chat_repository.get_conversation_detail(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ConversationDetail(**detail)


@router.post("/chat/send", response_model=SendMessageOut)
def send_message(payload: SendMessageIn) -> SendMessageOut:
    try:
        output = _chat_service.send_message(
            message=payload.message,
            conversation_id=payload.conversation_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return SendMessageOut(**output)


@router.get("/settings/system-prompt", response_model=SystemPromptOut)
def get_system_prompt() -> SystemPromptOut:
    return SystemPromptOut(system_prompt=_chat_service.get_system_prompt())


@router.put("/settings/system-prompt", response_model=SystemPromptOut)
def update_system_prompt(payload: SystemPromptUpdateIn) -> SystemPromptOut:
    prompt = _chat_service.update_system_prompt(payload.system_prompt)
    return SystemPromptOut(system_prompt=prompt)
