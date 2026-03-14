from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(slots=True)
class WakeWordEvent:
    phrase: str
    confidence: float
    detected_at: datetime


class WakeWordEngine(Protocol):
    async def start(self) -> None:
        """Start local wake-word monitoring."""

    async def stop(self) -> None:
        """Stop local wake-word monitoring."""


class AudioGateway(Protocol):
    async def mute(self) -> None:
        """Mute microphone and speaker output."""

    async def unmute(self) -> None:
        """Unmute microphone and speaker output."""

    async def interrupt_output(self) -> None:
        """Stop current playback immediately."""
