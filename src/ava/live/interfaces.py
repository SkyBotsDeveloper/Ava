from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class LiveSessionConfig:
    model_name: str
    locale: str = "en-IN"


class LiveSessionClient(Protocol):
    async def connect(self, config: LiveSessionConfig) -> None:
        """Open a Gemini Live session."""

    async def disconnect(self) -> None:
        """Close the Gemini Live session."""
