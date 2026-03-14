from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AssistantStatus(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


@dataclass(slots=True)
class AssistantState:
    status: AssistantStatus = AssistantStatus.IDLE
    muted: bool = False
    observation_enabled: bool = False
    last_command: str = ""
    last_response: str = ""
