from __future__ import annotations

from app.core.config import get_settings
from app.repositories.chat_repository import ChatRepository
from app.repositories.settings_repository import SettingsRepository
from app.services.openai_service import OpenAIService


class ChatService:
    def __init__(
        self,
        chat_repository: ChatRepository,
        settings_repository: SettingsRepository,
        openai_service: OpenAIService,
    ) -> None:
        self.chat_repository = chat_repository
        self.settings_repository = settings_repository
        self.openai_service = openai_service

    def get_system_prompt(self) -> str:
        settings = get_settings()
        prompt = self.settings_repository.get_value("system_prompt")
        if prompt:
            return prompt
        self.settings_repository.upsert_value("system_prompt", settings.system_prompt_default)
        return settings.system_prompt_default

    def update_system_prompt(self, system_prompt: str) -> str:
        self.settings_repository.upsert_value("system_prompt", system_prompt)
        return system_prompt

    def send_message(self, message: str, conversation_id: int | None) -> dict:
        if conversation_id is None:
            title = (message.strip()[:60] or "New Chat").replace("\n", " ")
            conversation = self.chat_repository.create_conversation(title=title)
            conversation_id = int(conversation["id"])

        user_message = self.chat_repository.add_message(
            conversation_id=conversation_id,
            role="user",
            content=message,
        )

        history = self.chat_repository.get_messages(conversation_id)
        system_prompt = self.get_system_prompt()
        assistant_text = self.openai_service.generate_reply(
            system_prompt=system_prompt,
            messages=history,
        )

        assistant_message = self.chat_repository.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_text,
        )
        conversation = self.chat_repository.get_conversation_summary(conversation_id)

        return {
            "conversation": conversation,
            "user_message": user_message,
            "assistant_message": assistant_message,
        }
