from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(slots=True)
class WakeWordEvent:
    phrase: str
    confidence: float
    detected_at: datetime


@dataclass(slots=True)
class AudioChunk:
    data: bytes
    sample_rate_hz: int
    captured_at: datetime


class WakeWordEngine(Protocol):
    async def start(self) -> None:
        """Start local wake-word monitoring."""

    async def stop(self) -> None:
        """Stop local wake-word monitoring."""

    async def process_chunk(self, chunk: AudioChunk) -> WakeWordEvent | None:
        """Inspect a chunk of microphone audio and return a wake-word hit if detected."""


class AudioGateway(Protocol):
    async def start_input(self) -> None:
        """Start microphone capture."""

    async def stop_input(self) -> None:
        """Stop microphone capture."""

    async def input_chunks(self) -> AsyncIterator[AudioChunk]:
        """Yield microphone audio chunks."""

    async def play_output_chunk(self, data: bytes, *, sample_rate_hz: int) -> None:
        """Play a chunk of output audio."""

    async def mute(self) -> None:
        """Mute microphone and speaker output."""

    async def unmute(self) -> None:
        """Unmute microphone and speaker output."""

    async def interrupt_output(self) -> None:
        """Stop current playback immediately."""
