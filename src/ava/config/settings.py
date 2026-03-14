from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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

    gemini_live_model: str = "gemini-2.5-flash-native-audio-preview-12-2025"
    gemini_live_api_version: str = "v1beta"
    gemini_api_key: str | None = None
    gemini_live_locale: str = "en-IN"
    gemini_live_voice_name: str = "Kore"
    gemini_live_enable_server_vad: bool = False
    gemini_live_vad_prefix_padding_ms: int = Field(default=180, ge=0, le=3000)
    gemini_live_vad_silence_ms: int = Field(default=700, ge=100, le=5000)
    gemini_live_enable_input_transcription: bool = True
    gemini_live_enable_output_transcription: bool = True
    gemini_live_thinking_budget: int = Field(default=0, ge=0, le=24576)

    voice_input_sample_rate_hz: int = Field(default=16_000, ge=8000, le=48_000)
    voice_output_sample_rate_hz: int = Field(default=24_000, ge=8000, le=48_000)
    voice_input_chunk_ms: int = Field(default=80, ge=20, le=1000)
    wakeword_model_paths: Annotated[tuple[str, ...], NoDecode] = ()
    wakeword_trigger_phrase: str = "Ava"
    wakeword_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    wakeword_patience_frames: int = Field(default=1, ge=1, le=20)

    observation_enabled: bool = False
    observation_sampling_seconds: float = Field(default=10.0, ge=1.0, le=3600.0)
    observation_private_processes: Annotated[tuple[str, ...], NoDecode] = (
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

    @field_validator("observation_private_processes", "wakeword_model_paths", mode="before")
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
