from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol


class ResponseModality(StrEnum):
    AUDIO = "AUDIO"
    TEXT = "TEXT"


@dataclass(slots=True)
class LiveSessionConfig:
    model_name: str
    locale: str = "en-IN"
    voice_name: str = "Kore"
    response_modalities: tuple[ResponseModality, ...] = field(
        default_factory=lambda: (ResponseModality.AUDIO,)
    )
    system_instruction: str = ""
    input_sample_rate_hz: int = 16_000
    output_sample_rate_hz: int = 24_000
    enable_input_transcription: bool = True
    enable_output_transcription: bool = True
    enable_server_vad: bool = True
    vad_prefix_padding_ms: int = 180
    vad_silence_ms: int = 700
    thinking_budget: int = 512


@dataclass(slots=True)
class TranscriptEvent:
    text: str
    is_input: bool
    is_final: bool = False


@dataclass(slots=True)
class AudioChunkEvent:
    data: bytes
    mime_type: str = "audio/pcm;rate=24000"


@dataclass(slots=True)
class TurnBoundaryEvent:
    phase: str
    reason: str | None = None


@dataclass(slots=True)
class VoiceActivityEvent:
    phase: str


class LiveSessionClient(Protocol):
    async def connect(self, config: LiveSessionConfig) -> None:
        """Open a Gemini Live session."""

    async def disconnect(self) -> None:
        """Close the Gemini Live session."""

    async def send_text(self, text: str, *, end_of_turn: bool = True) -> None:
        """Send a text turn into the live session."""

    async def send_audio_chunk(self, pcm_bytes: bytes, *, mime_type: str) -> None:
        """Stream a chunk of realtime PCM audio to Gemini Live."""

    async def send_activity_start(self) -> None:
        """Signal manual speech activity start to Gemini Live."""

    async def send_activity_end(self) -> None:
        """Signal manual speech activity end to Gemini Live."""

    async def receive(
        self,
    ) -> AsyncIterator[TranscriptEvent | AudioChunkEvent | TurnBoundaryEvent | VoiceActivityEvent]:
        """Yield normalized events from the live session."""
