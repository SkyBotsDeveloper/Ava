from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AVA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = "development"
    app_name: str = "Ava"
    log_level: str = "INFO"
    debug: bool = False
    data_root: Path | None = None

    preferred_browser: Literal["edge", "chrome"] = "edge"
    browser_live_session_first: bool = True
    launch_edge_when_browser_missing: bool = True

    gemini_live_model: str = "gemini-live-2.5-flash-preview"
    gemini_api_key: str | None = None

    observation_enabled: bool = False
    observation_sampling_seconds: float = Field(default=10.0, ge=1.0, le=3600.0)
    observation_private_processes: tuple[str, ...] = (
        "1password",
        "bitwarden",
        "keepass",
        "lastpass",
        "bank",
        "wallet",
    )

    push_to_talk_hotkey: str = "ctrl+alt+a"
    mute_hotkey: str = "ctrl+alt+m"
    emergency_stop_hotkey: str = "ctrl+alt+backspace"
    ui_auto_close_ms: int = Field(default=0, ge=0, le=60000)

    @field_validator("observation_private_processes", mode="before")
    @classmethod
    def validate_private_processes(
        cls, value: tuple[str, ...] | list[str] | str
    ) -> tuple[str, ...]:
        if isinstance(value, str):
            return tuple(item.strip() for item in value.split(",") if item.strip())
        return tuple(value)


def load_settings(env_file: str | Path | None = ".env") -> Settings:
    if env_file is None:
        return Settings(_env_file=None)
    return Settings(_env_file=env_file)
