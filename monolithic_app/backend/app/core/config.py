from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    openai_mock: bool
    system_prompt_default: str
    database_path: str


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_settings() -> Settings:
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        openai_mock=_as_bool(os.getenv("OPENAI_MOCK"), default=False),
        system_prompt_default=os.getenv(
            "SYSTEM_PROMPT", "You are a concise and helpful assistant."
        ),
        database_path=os.getenv("DATABASE_PATH", "./chat.db"),
    )
