from __future__ import annotations

from typing import Any

from openai import OpenAI

from app.core.config import get_settings


class OpenAIService:
    def __init__(self) -> None:
        self._client: OpenAI | None = None

    def generate_reply(self, system_prompt: str, messages: list[dict[str, Any]]) -> str:
        settings = get_settings()
        if settings.openai_mock:
            latest = next((m for m in reversed(messages) if m["role"] == "user"), None)
            text = latest["content"] if latest else ""
            return f"[MOCK] I received: {text[:120]}"

        if self._client is None and settings.openai_api_key:
            self._client = OpenAI(api_key=settings.openai_api_key)

        if self._client is None:
            raise RuntimeError("OPENAI_API_KEY is missing. Set it in environment or .env.")

        response = self._client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": system_prompt},
                *[
                    {
                        "role": m["role"],
                        "content": m["content"],
                    }
                    for m in messages
                ],
            ],
        )
        text = response.output_text.strip()
        if not text:
            raise RuntimeError("OpenAI returned an empty response.")
        return text
